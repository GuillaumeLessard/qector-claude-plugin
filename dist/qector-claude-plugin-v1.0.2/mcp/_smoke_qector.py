"""Check qector_decoder_v3 import status."""

try:
    import qector_decoder_v3

    print("IMPORTED OK")
    print("version:", qector_decoder_v3.__version__)
    print("has UnionFindDecoder:", hasattr(qector_decoder_v3, "UnionFindDecoder"))
    print("has codes:", hasattr(qector_decoder_v3, "codes"))
    print("has BlossomDecoder:", hasattr(qector_decoder_v3, "BlossomDecoder"))
    print("has cuda_is_available:", hasattr(qector_decoder_v3, "cuda_is_available"))
    print("has opencl_is_available:", hasattr(qector_decoder_v3, "opencl_is_available"))
    print("has pymatching_compat:", hasattr(qector_decoder_v3, "pymatching_compat"))
    print("has get_license_info:", hasattr(qector_decoder_v3, "get_license_info"))
    print(
        "has qector_sinter_decoders:",
        hasattr(qector_decoder_v3, "qector_sinter_decoders"),
    )
    print("has qiskit_plugin:", hasattr(qector_decoder_v3, "qiskit_plugin"))
    if hasattr(qector_decoder_v3, "codes"):
        print("codes module:", dir(qector_decoder_v3.codes))
except Exception as exc:
    print(f"IMPORT FAILED: {type(exc).__name__}: {exc}")
