# Build & Environment Log: ENCIDER Real Toolchain

## 1. System Environment

- **Operating System:** Microsoft Windows 10 Home/Pro (Build 19045.6456, amd64)
- **User Execution Context:** Non-elevated user (`Admin`), standard PowerShell 5.1 session
- **Installed Docker Client:** Docker Desktop 29.6.2 (Context: `desktop-linux`, Git commit `dfc4efb`)
- **Repository Under Test:** `https://github.com/sysrel/ENCIDER` (Commit `2e5408387fa48923128bae73529401ff34e70937`)

---

## 2. Docker Toolchain Build Attempt

The reference Dockerfile for building ENCIDER is provided in `baseline/Dockerfile`, targeting an Ubuntu 16.04 base image with `clang-3.8`, `llvm-3.8`, `z3`, and KLEE 1.4.0 dependencies.

### Command Execution:
```powershell
docker version
```

### Output:
```text
Client:
 Version:           29.6.2
 API version:       1.55
 Go version:        go1.26.5
 Git commit:        dfc4efb
 Built:             Thu Jul 16 16:14:59 2026
 OS/Arch:           windows/amd64
 Context:           desktop-linux
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

---

## 3. Root Cause Investigation in Docker Desktop Engine

Inspection of Docker Desktop's host engine log file (`C:\Users\Admin\AppData\Local\Docker\log\host\com.docker.backend.exe.log`) revealed the exact blocking precondition failure:

```text
[com.docker.backend.exe.engines][W] attempting recovery from engine failure: starting engine: engine linux/wsl failed to start: checking preconditions: Virtual Machine Platform not enabled
[com.docker.backend.exe.engines][W] no virtualization found: starting engine: engine linux/wsl failed to start: checking preconditions: Virtual Machine Platform not enabled
```

Docker Desktop relies on either the Windows Subsystem for Linux (WSL 2) backend or Hyper-V to run Linux containers. Neither feature is enabled on this host.

---

## 4. Remediation Attempts & Privilege Restrictions

To bring up the Linux engine, we attempted to inspect and enable WSL and the Virtual Machine Platform feature:

1. **Attempted command:** `C:\Windows\System32\wsl.exe --status`
   - **Result:** Exited with code 1.
2. **Attempted command:** `C:\Windows\System32\wsl.exe --install --no-distribution`
   - **Result:**
     ```text
     The request is not supported.
     The requested operation requires elevation.
     ```
3. **Attempted command:** `dism.exe /online /get-featureinfo /featurename:VirtualMachinePlatform`
   - **Result:**
     ```text
     Deployment Image Servicing and Management tool
     Version: 10.0.19041.3636

     Error: 740
     An elevated command prompt is required to run DISM.
     Use an elevated command prompt to complete these tasks.
     ```

Because the agent environment operates in a standard, non-elevated user shell without UAC prompt bypass, enabling Windows OS kernel features (`VirtualMachinePlatform`, `Microsoft-Windows-Subsystem-Linux`) is strictly prohibited by Windows security boundaries.

---

## 5. Host Native Compilation Inspection

We examined whether native build tools could compile ENCIDER directly without Docker:

1. **Compilers available on host PATH:**
   - Cygwin (`C:\cygwin64\bin\gcc.exe`, `g++.exe` v13.4.0, `make.exe`)
   - No `clang`, `clang++`, or `llvm-config` found on PATH or anywhere on `C:\` or `D:\`.
2. **Compatibility requirements of ENCIDER:**
   - Requires LLVM 3.8 / Clang 3.8 C++ headers and libraries (`llvm-config-3.8`).
   - Requires Linux POSIX system headers (`<sys/mman.h>`, signal masks, ELF execution structures).
   - KLEE 1.4.0 does not support MSVC or native Windows compilation.

---

## 6. Exact Steps to Unblock Build & Execution

To compile the container and run the benchmarks on this machine or any development machine:

1. **On Windows (Administrator Elevation Required):**
   Open an Administrator PowerShell prompt and run:
   ```powershell
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   wsl.exe --update
   ```
   Reboot Windows. Once rebooted, launch Docker Desktop.

2. **Alternatively (On any Linux / Ubuntu x86_64 Host):**
   ```bash
   git clone https://github.com/Shrawanichaudhari/ENCIDER-Detecting-Timing-and-Cache-Side-Channels-in-SGX-Enclaves-and-Cryptographic-APIs.git
   cd ENCIDER-Detecting-Timing-and-Cache-Side-Channels-in-SGX-Enclaves-and-Cryptographic-APIs
   docker build -t encider:baseline -f baseline/Dockerfile .
   ```

3. **Applying the Patched Scheduler Inside the Container:**
   ```bash
   cd /opt/ENCIDER
   git apply /path/to/real_encider_eval/encider_riskguided.patch
   cd /opt/encider_build
   make -j$(nproc)
   ```

4. **Running the Benchmarks:**
   Execute `real_encider_eval/run_encider_experiment.sh`.
