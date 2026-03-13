from __future__ import annotations

from dataclasses import dataclass, field


ACCURACY_PROFILE = "accuracy"
FALLBACK_PROFILE = "balanced"


@dataclass(slots=True)
class ProfileState:
    requested_profile: str = ACCURACY_PROFILE
    active_profile: str = ACCURACY_PROFILE
    fallback_active: bool = False
    fallback_reason: str | None = None


@dataclass
class AccuracyProfileController:
    overload_cpu_threshold: float = 0.9
    recover_cpu_threshold: float = 0.6
    overload_windows: int = 3
    recover_windows: int = 3
    state: ProfileState = field(default_factory=ProfileState)
    _high_cpu_windows: int = 0
    _low_cpu_windows: int = 0

    def observe_cpu_load(self, cpu_load: float | None) -> ProfileState:
        if cpu_load is None:
            return self.state

        if self.state.fallback_active:
            if cpu_load <= self.recover_cpu_threshold:
                self._low_cpu_windows += 1
            else:
                self._low_cpu_windows = 0

            if self._low_cpu_windows >= self.recover_windows:
                self.state.active_profile = self.state.requested_profile
                self.state.fallback_active = False
                self.state.fallback_reason = None
                self._high_cpu_windows = 0
                self._low_cpu_windows = 0
            return self.state

        if cpu_load >= self.overload_cpu_threshold:
            self._high_cpu_windows += 1
        else:
            self._high_cpu_windows = 0

        if self._high_cpu_windows >= self.overload_windows:
            self.state.active_profile = FALLBACK_PROFILE
            self.state.fallback_active = True
            self.state.fallback_reason = "sustained_cpu_pressure"
            self._high_cpu_windows = 0
            self._low_cpu_windows = 0

        return self.state
