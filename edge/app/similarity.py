import numpy as np


def cosine_distance(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = np.linalg.norm(left)
    right_norm = np.linalg.norm(right)
    if left_norm == 0 or right_norm == 0:
        return 1.0
    similarity = float(np.dot(left, right) / (left_norm * right_norm))
    return 1.0 - similarity

