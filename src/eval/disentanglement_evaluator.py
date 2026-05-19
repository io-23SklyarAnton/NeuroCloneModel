import math
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, mutual_info_score


class DisentanglementEvaluator:
    def __init__(self, ground_truth: dict[Any, Any], predictions: dict[Any, Any]):
        self.gt_normalized = {str(k): v for k, v in ground_truth.items()}
        self.pred_normalized = {str(k): v for k, v in predictions.items()}

        try:
            self.message_ids = sorted(list(self.gt_normalized.keys()), key=int)
        except ValueError:
            self.message_ids = sorted(list(self.gt_normalized.keys()))

        self.total_messages = len(self.message_ids)
        self.y_true = []
        self.y_pred = []

        for mid in self.message_ids:
            self.y_true.append(self.gt_normalized[mid])

            p_id = self.pred_normalized.get(mid)
            if p_id is None:
                p_id = f"UNASSIGNED_{mid}"

            self.y_pred.append(p_id)

        self.true_clusters = defaultdict(set)
        self.pred_clusters = defaultdict(set)

        for mid, t_id, p_id in zip(self.message_ids, self.y_true, self.y_pred):
            self.true_clusters[t_id].add(mid)
            self.pred_clusters[p_id].add(mid)

        self.true_sets = list(self.true_clusters.values())
        self.pred_sets = list(self.pred_clusters.values())

    def calculate_ari(self) -> float:
        return adjusted_rand_score(self.y_true, self.y_pred) * 100

    def calculate_nmi(self) -> float:
        return normalized_mutual_info_score(self.y_true, self.y_pred) * 100

    def calculate_vi(self) -> float:
        def calculate_entropy(labels):
            probs = [count / self.total_messages for count in Counter(labels).values()]
            return -sum(p * np.log(p) for p in probs)

        h_true = calculate_entropy(self.y_true)
        h_pred = calculate_entropy(self.y_pred)
        mi = mutual_info_score(self.y_true, self.y_pred)

        vi_raw = h_true + h_pred - 2 * mi

        max_vi = math.log(self.total_messages) if self.total_messages > 1 else 1.0
        scaled_vi = max(0.0, 1.0 - (vi_raw / max_vi))
        return scaled_vi * 100

    def calculate_1_to_1(self) -> float:
        cost_matrix = np.zeros((len(self.true_sets), len(self.pred_sets)))
        for i, t_set in enumerate(self.true_sets):
            for j, p_set in enumerate(self.pred_sets):
                cost_matrix[i, j] = -len(t_set.intersection(p_set))

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        optimal_overlap = -cost_matrix[row_ind, col_ind].sum()

        return (optimal_overlap / self.total_messages) * 100

    def calculate_local3(self) -> float:
        correct_pairs = 0
        total_pairs = 0

        for i in range(self.total_messages):
            for j in range(i + 1, min(i + 4, self.total_messages)):
                true_match = (self.y_true[i] == self.y_true[j])
                pred_match = (self.y_pred[i] == self.y_pred[j])

                if true_match == pred_match:
                    correct_pairs += 1
                total_pairs += 1

        return (correct_pairs / total_pairs) * 100 if total_pairs > 0 else 0.0

    def calculate_shen_f1(self) -> float:
        weighted_f1_sum = 0.0

        for t_set in self.true_sets:
            max_f1 = 0.0
            for p_set in self.pred_sets:
                intersection = len(t_set.intersection(p_set))
                if intersection == 0:
                    continue

                precision = intersection / len(p_set)
                recall = intersection / len(t_set)

                if precision + recall > 0:
                    f1 = (2 * precision * recall) / (precision + recall)
                    if f1 > max_f1:
                        max_f1 = f1

            weighted_f1_sum += max_f1 * (len(t_set) / self.total_messages)

        return weighted_f1_sum * 100

    def calculate_exact_match(self) -> dict[str, float]:
        frozen_true = [frozenset(c) for c in self.true_sets]
        frozen_pred = [frozenset(c) for c in self.pred_sets]

        exact_matches = sum(1 for p_set in frozen_pred if p_set in frozen_true)

        precision = exact_matches / len(frozen_pred) if frozen_pred else 0.0
        recall = exact_matches / len(frozen_true) if frozen_true else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "P": precision * 100,
            "R": recall * 100,
            "F1": f1 * 100
        }

    def get_all_metrics(self) -> dict[str, float]:
        exact = self.calculate_exact_match()
        return {
            "VI": self.calculate_vi(),
            "ARI": self.calculate_ari(),
            "NMI": self.calculate_nmi(),
            "1-1": self.calculate_1_to_1(),
            "Local3": self.calculate_local3(),
            "Shen-F1": self.calculate_shen_f1(),
            "P": exact["P"],
            "R": exact["R"],
            "F1": exact["F1"]
        }

    def print_report(self):
        metrics = self.get_all_metrics()
        print("-" * 45)
        print(f"{'Metric':<15} | {'Score (0-100)':<15}")
        print("-" * 45)
        for name, score in metrics.items():
            print(f"{name:<15} | {score:.2f}")
        print("-" * 45)
