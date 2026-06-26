class CalibrationAlgorithm:
    """Available wavelength-calibration peak-matching algorithms.

    HEURISTIC is the prominence-based anchor-and-grow matcher. RANSAC and RANSAC_SEEDED use the
    rascal library (Hough + RANSAC) against the CFL atlas — standalone, and seeded with the
    heuristic's cubic as rascal's starting solution. The selection box lets the user pick.
    """

    HEURISTIC = "HEURISTIC"
    HEURISTIC_ADVANCED = "HEURISTIC_ADVANCED"
    HEURISTIC_PRO = "HEURISTIC_PRO"
    RANSAC = "RANSAC"
    RANSAC_SEEDED = "RANSAC_SEEDED"

    # ordered (value, display label, implemented?)
    # The single "Heuristic" entry runs a CONSENSUS: simple heuristic + advanced (predict-and-snap) +
    # colour + green-doublet cross-checks on the five anchor lines, to raise confidence in them.
    # ADVANCED / PRO / RANSAC remain as internal constants but are no longer offered as separate options.
    ALL = [
        (HEURISTIC, "Heuristic", True),
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
