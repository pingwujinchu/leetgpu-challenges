from typing import Dict, Any, List

class ChallengeBase:
    def __init__(self, name: str, atol: float, rtol: float, num_gpus: int = 1, access_tier: str = "free") -> None:
        self.name = name
        self.atol = atol
        self.rtol = rtol
        self.num_gpus = num_gpus
        self.access_tier = access_tier

    # Expected to be implemented by subclasses
    def reference_impl(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def get_solve_signature(self) -> Dict[str, tuple]:  # pragma: no cover
        raise NotImplementedError

    def generate_example_test(self) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def generate_functional_test(self) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    def generate_performance_test(self) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError
