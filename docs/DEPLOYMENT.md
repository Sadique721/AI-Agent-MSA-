# Deployment & Run Manual — MSA AI Agent V4.5

Details script commands to install, run, and package the V4.5 ecosystem.

## Commands List

- **Initialize virtualenv**:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\activate
  pip install -r requirements.txt
  ```
- **Run Python server**:
  ```powershell
  python main.py
  ```
- **Launch Electron Client**:
  ```powershell
  cd frontend-desktop
  npm install
  npm start
  ```
