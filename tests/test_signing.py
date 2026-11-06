"""Ed25519 release signing: round-trip, tamper detection, pinned-key gate,
and the Python 3.10 syntax floor for every shipped module."""

from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
os.environ.setdefault("QECTOR_SILENT", "1")


class SigningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="qector-sign-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _tree(self, public_key: str | None = None) -> Path:
        import qector_integrity

        tree = self.tmp / "tree"
        (tree / "mcp").mkdir(parents=True)
        (tree / "mcp" / "a.py").write_text("x = 1\n", encoding="utf-8")
        (tree / "requirements.txt").write_text("numpy\n", encoding="utf-8")
        if public_key is not None:
            (tree / "release-manifest.json").write_text(json.dumps({"signing": {"public_key": public_key}}), encoding="utf-8")
        manifest = qector_integrity.build_manifest(tree, version="2.0.0")
        (tree / qector_integrity.MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return tree

    def test_sign_verify_tamper_and_wrong_key(self) -> None:
        import qector_integrity
        import qector_signing

        key = qector_signing.generate_private_key(self.tmp / "k.pem")
        other = qector_signing.generate_private_key(self.tmp / "k2.pem")
        public = qector_signing.public_key_b64(key)
        self.assertEqual(len(qector_signing.fingerprint(public)), 64)
        tree = self._tree(public)
        manifest_path = tree / qector_integrity.MANIFEST_NAME
        payload = manifest_path.read_bytes()
        (tree / "INTEGRITY.json.sig").write_text(
            json.dumps(qector_signing.signature_document(key, payload, subject="INTEGRITY.json")), encoding="utf-8"
        )
        # Consistency (embedded key) and origin (pinned key) both verify.
        report = qector_integrity.verify(tree, strict=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["signature"]["source"], "release_manifest")
        report = qector_integrity.verify(tree, strict=True, pinned_public_key=public)
        self.assertTrue(report["passed"])
        self.assertEqual(report["signature"]["source"], "pinned")
        # Wrong pinned key: refused even though the embedded signature is consistent.
        report = qector_integrity.verify(tree, strict=True, pinned_public_key=qector_signing.public_key_b64(other))
        self.assertFalse(report["passed"])
        self.assertIn("pinned", report["signature"]["reason"])
        # Tampered manifest bytes: signature no longer verifies.
        manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        report = qector_integrity.verify(tree, strict=True, pinned_public_key=public)
        self.assertFalse(report["signature"]["valid"])
        self.assertFalse(report["passed"])
        # Re-signed by an attacker with their own key but the declared key untouched:
        # refused even without pinning.
        manifest_path.write_text(payload.decode("utf-8"), encoding="utf-8")
        (tree / "INTEGRITY.json.sig").write_text(
            json.dumps(qector_signing.signature_document(other, payload, subject="INTEGRITY.json")), encoding="utf-8"
        )
        rekeyed = qector_integrity.verify(tree, strict=True)
        self.assertFalse(rekeyed["passed"])
        self.assertIn("declared", rekeyed["signature"]["reason"])
        # Re-signed by an attacker with their own key AND a swapped declared key:
        # consistency passes, origin under the pinned key fails.
        (tree / "INTEGRITY.json.sig").write_text(
            json.dumps(qector_signing.signature_document(other, manifest_path.read_bytes(), subject="INTEGRITY.json")),
            encoding="utf-8",
        )
        # (the attacker must also rebuild the manifest so release-manifest.json's new hash matches)
        (tree / "release-manifest.json").write_text(
            json.dumps({"signing": {"public_key": qector_signing.public_key_b64(other)}}), encoding="utf-8"
        )
        forged = qector_integrity.build_manifest(tree, version="2.0.0")
        manifest_path.write_text(json.dumps(forged, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (tree / "INTEGRITY.json.sig").write_text(
            json.dumps(qector_signing.signature_document(other, manifest_path.read_bytes(), subject="INTEGRITY.json")),
            encoding="utf-8",
        )
        self.assertTrue(qector_integrity.verify(tree, strict=True)["passed"])
        self.assertFalse(qector_integrity.verify(tree, strict=True, pinned_public_key=public)["passed"])

    def test_unsigned_tree_passes_on_files_but_reports_it(self) -> None:
        import qector_integrity

        tree = self._tree()
        report = qector_integrity.verify(tree, strict=True)
        self.assertTrue(report["passed"])
        self.assertFalse(report["signature"]["present"])
        self.assertEqual(report["signature"]["reason"], "release is unsigned")
        # A pinned key with no signature at all must not pass.
        pinned = qector_integrity.verify(tree, strict=True, pinned_public_key="A" * 43 + "=")
        self.assertFalse(pinned["passed"])
        self.assertEqual(pinned["signature"]["source"], "none")

    def test_hostile_manifests_and_keys_never_escape_the_root(self) -> None:
        import qector_integrity
        import qector_signing

        tree = self._tree()
        manifest = tree / qector_integrity.MANIFEST_NAME
        outside = tree.parent / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        hostile = {
            "traversal": {"files": {"../outside.txt": qector_integrity.sha256_file(outside)}},
            "absolute": {"files": {str(outside): qector_integrity.sha256_file(outside)}},
            "non_runtime": {"files": {"README.md": "0" * 64}},
            "bad_digest": {"files": {"mcp/a.py": "zz"}},
            "pairs": {"files": [["mcp/a.py", "0" * 64]]},
            "scalar": {"files": "x"},
            "list": [],
        }
        for label, payload in hostile.items():
            with self.subTest(case=label):
                manifest.write_text(json.dumps(payload), encoding="utf-8")
                report = qector_integrity.verify(tree, strict=True)
                self.assertFalse(report["passed"])
                self.assertTrue(report["mismatched"], label)
        manifest.write_text(json.dumps(qector_integrity.build_manifest(tree, version="t"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # A mistyped pinned key is a configuration error, not a traceback.
        for bad in ("not-b64!", "AAAA", "A" * 43 + "="):
            with self.subTest(key=bad):
                if bad == "A" * 43 + "=":
                    # well-formed but unknown key: simply does not verify
                    report = qector_integrity.verify(tree, strict=True, pinned_public_key=bad)
                    self.assertFalse(report["passed"])
                    continue
                with self.assertRaises(qector_signing.QECTORSignatureError):
                    qector_signing.fingerprint(bad)
                report = qector_integrity.verify(tree, strict=True, pinned_public_key=bad)
                self.assertFalse(report["passed"])
                self.assertIn("rejected", report["signature"]["reason"])
        # Hostile signature documents are reported, never raised.
        sig = tree / (qector_integrity.MANIFEST_NAME + qector_signing.SIGNATURE_SUFFIX)
        for doc in ("{}", "[]", "null", "not json", '{"public_key": 1, "signature": 2}', '{"public_key": null, "signature": null}'):
            with self.subTest(doc=doc):
                sig.write_text(doc, encoding="utf-8")
                report = qector_signing.verify_signature_file(manifest, pinned_public_key="A" * 43 + "=")
                self.assertFalse(report["valid"])
                self.assertIsNotNone(report["reason"])

    def test_release_manifest_declares_a_real_key(self) -> None:
        import qector_signing

        release = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
        signing = release["signing"]
        self.assertEqual(signing["algorithm"], "ed25519")
        self.assertEqual(qector_signing.fingerprint(signing["public_key"]), signing["fingerprint"])
        qector_signing.load_public_key(signing["public_key"])
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn(signing["fingerprint"], security, "SECURITY.md must publish the signing key fingerprint")


class SyntaxFloorTests(unittest.TestCase):
    def test_every_module_parses_as_python_3_10(self) -> None:
        for directory in ("mcp", "scripts", "python", "tests"):
            for path in sorted((ROOT / directory).rglob("*.py")):
                with self.subTest(file=str(path.relative_to(ROOT))):
                    ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 10))


if __name__ == "__main__":
    unittest.main()
