"""Cost-sensitive decision boundary."""


def bayes_threshold(cost_fn: float, cost_fp: float) -> float:
    """Elkan (2001), The Foundations of Cost-Sensitive Learning, IJCAI.

    Review when (1-p) C_FP <= p C_FN, hence p >= C_FP/(C_FP+C_FN).
    Costs come from configs/policy.yaml, never from fitted Indian outcomes.
    """
    if cost_fn <= 0 or cost_fp <= 0:
        raise ValueError("Costs must be positive")
    return cost_fp / (cost_fp + cost_fn)
