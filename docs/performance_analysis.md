# Performance Analysis

This document outlines the performance characteristics of the `xgamma_gui_tool` and provides recommendations for optimization.

## 1. Subprocess Calls on Slider Change (Fixed)

### Original Issue
The application initially called the `applyGamma()` method, which executes an `xgamma` subprocess, on every single tick of a slider's movement.

### Impact
- **High Latency:** Each subprocess call has an inherent overhead (approx. 30-50ms).
- **Command Queuing:** Rapid slider movement could lead to a queue of pending `xgamma` commands, causing unresponsive or unpredictable behavior.

### Resolution (Implemented)
The issue has been resolved by introducing a `QTimer` (`gammaApplyTimer`) to debounce the `applyGamma()` calls.
- A timer with a 50ms delay is now used.
- The gamma values are only applied after the user has stopped moving the slider for a brief period.
- This significantly reduces the number of subprocess calls and improves UI responsiveness.

---

## 2. Potential Areas for Further Optimization

While the most critical performance issue is resolved, the following areas could be improved for an even better user experience.

### 2.1. Blocking Calls on Application Startup

### Issue
During initialization, the application makes several blocking `subprocess` calls to determine the environment and initial gamma state:
- `gammaCore.getCurrentGamma()` (calls `xgamma` and potentially `xrandr`)
- `_collectEnvironmentWarnings()` (calls `systemd-detect-virt` and `xrandr`)

### Impact
- **Delayed Startup:** These synchronous calls can delay the appearance of the main window, especially on slower systems or if the command-line tools are slow to respond. The perceived startup time is increased.

### Recommendations
- **Asynchronous Initialization:** Move these checks to a separate worker thread (`QThread`).
    1. The GUI can be shown immediately with default values (e.g., gamma 1.0) and a "Loading..." status.
    2. The worker thread runs the detection functions in the background.
    3. Once complete, the thread emits a signal with the results (current gamma, warnings).
    4. The main window listens for this signal and updates the UI accordingly.
- **Benefit:** This would make the application feel much faster to launch, as the UI would be interactive almost instantly.

### 2.2. Reference Image Generation

### Issue
The `ReferenceImageGenerator.generateImage()` method redraws a `QPixmap` every time the gamma changes. While this is throttled by `imageUpdateTimer`, the generation itself can be CPU-intensive.

### Analysis
- The current implementation is already optimized by using a `QTimer`, which is sufficient for most use cases. The image size is fixed, and the drawing operations are reasonably fast on modern hardware.

### Recommendations
- **No Action Required (Currently):** The existing timer-based throttling is an effective and adequate solution. Further optimization (e.g., caching layers of the image) would add significant complexity for minimal real-world gain.

### 2.3. Caching Environment Checks

### Issue
The `_isVirtualMachine()` and `_isHdrPipelineActive()` helper functions may be called multiple times, and each call invokes a subprocess.

### Impact
- **Minor Redundancy:** The results of these checks will not change during the application's lifecycle. Re-running the subprocesses is unnecessary.

### Recommendations
- **Cache Results:** Store the results of the first call in an instance variable. Subsequent calls should return the cached value.
    ```python
    # In GammaMainWindow.__init__
    self._vm_check_result = None

    # In _isVirtualMachine
    if self._vm_check_result is None:
        # ... perform detection logic ...
        self._vm_check_result = result
    return self._vm_check_result
    ```
- **Benefit:** This is a simple, low-effort optimization that eliminates redundant process calls.