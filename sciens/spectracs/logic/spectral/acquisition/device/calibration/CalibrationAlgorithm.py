class CalibrationAlgorithm:
    """Available wavelength-calibration peak-matching algorithms.

    HEURISTIC is the prominence-based anchor-and-grow matcher. RANSAC and RANSAC_SEEDED use the
    rascal library (Hough + RANSAC) against the CFL atlas — standalone, and seeded with the
    heuristic's cubic as rascal's starting solution. The selection box lets the user pick.
    """

    HEURISTIC = "HEURISTIC"
    RANSAC = "RANSAC"
    RANSAC_SEEDED = "RANSAC_SEEDED"

    # ordered (value, display label, implemented?)
    ALL = [
        (HEURISTIC, "Heuristic (prominence)", True),
        (RANSAC, "RANSAC (standalone)", True),
        (RANSAC_SEEDED, "RANSAC (seeded by heuristic)", True),
    ]

    @staticmethod
    def isImplemented(algorithm: str) -> bool:
        for value, _label, implemented in CalibrationAlgorithm.ALL:
            if value == algorithm:
                return implemented
        return False

    @staticmethod
    def getLabel(algorithm: str) -> str:
        for value, label, _implemented in CalibrationAlgorithm.ALL:
            if value == algorithm:
                return label
        return algorithm
