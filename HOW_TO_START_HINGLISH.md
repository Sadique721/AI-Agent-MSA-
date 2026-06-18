# 🚀 MSA Project Ko Kaise Start Karein (Step-by-Step Guide)

Is guide me bataya gaya hai ki aap kisi bhi terminal (PowerShell, Command Prompt, ya Git Bash) ka use karke backend server, Android emulator, aur updated APK ko kaise start aur verify karenge.

---

## 📋 Prerequisite (Pehle Se Kya Installed Hona Chahiye)
1. **Python 3.14+** aapke system par path me hona chahiye.
2. **Android SDK & platform-tools** (`adb.exe` ke liye) installed aur path me configure hona chahiye.
3. **Java JDK 17+** (Gradle compile karne ke liye).

---

## 🛠️ Step-by-Step Instructions

### Step 1: Terminal Open Karein Aur Project Folder Me Jayein
Sabse pehle apna terminal open karein aur project ke main path (`d:\My Self Details\Programs\AI\msa_agent`) par jayein:
```bash
cd "d:\My Self Details\Programs\AI\msa_agent"
```

---

### Step 2: Python Backend Server Ko Start Karein
Backend server ko background me chalane ke liye niche likhi command run karein. Ye server mobile connection aur RAG memory database ko handle karega:
```bash
python main.py
```
> 💡 **Tip**: Server chalne ke baad `http://localhost:5000` par active ho jayega. Ise open chhod dein aur naya terminal tab open karein agle steps ke liye.

---

### Step 3: Android Emulator Ko Start Karein
Naye terminal window me Android Emulator ko SwiftShader soft-rendering ke sath chalayein (taaki computer graphics driver me koi error na aaye aur emulator crash na ho):
```bash
& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd medium_phone -no-audio -no-boot-anim -gpu swiftshader_indirect
```
> 💡 **Tip**: Emulator ko poori tarah load hone dein jab tak ki home screen na dikhe. `adb devices` run karke verify kar sakte hain ki device connected hai ya nahi:
> `& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices`

---

### Step 4: Final Android App APK Ko Build Karein
Android app ke code ko compile aur build karne ke liye root directory se build script ko run karein:
```bash
cd "d:\My Self Details\Programs\AI\msa_agent"
powershell -ExecutionPolicy Bypass -File .\scripts\setup_flutter_and_build.ps1
```
> 💡 **Note**: Jab build successful ho jaye, to aapka latest APK root folder me `msa_agent_client.apk` naam se save ho jayega.

---

### Step 5: Emulator Par APK Install Aur Start Karein
Naye compiled APK ko emulator me install karne ke liye main directory se ye command run karein:
```bash
cd "d:\My Self Details\Programs\AI\msa_agent"
& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r "d:\My Self Details\Programs\AI\msa_agent\msa_agent_client.apk"
```
Install hone ke baad, app ko emulator me directly start karne ke liye:
```bash
& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msaaiagent.msa_ai_agent/com.msaaiagent.msa_ai_agent.MainActivity
```
App open hone par status check karein:
- Top right corner me settings icon (gear) par click karke PC server ka actual IP address setup karein.
- Green color me **Agent Online** status aana chahiye, jo connection verify karta hai.

---

### Step 6: Unit Tests Ko Run Karein (Verification Ke Liye)
Agar aapko saare backend logic, coding generator, validator, aur review system ke unit tests check karne hain, to project ke main path se pytest command run karein (dhyaan rahe ki target directory `tests/` ko specify karein):
```bash
python -m pytest tests/
```
> 🧪 **Result**: Saare **419 test cases** 100% pass hone chahiye bina kisi error ke.

---

## 📱 Developer/Coding Agent Activities Ko Kaise Launch Karein
Naye unified Flutter app main, sabhi coding activities (Code Reviewer, StackTrace, Project Scaffolder, History) dashboard page par tab interfaces aur menus ke roop me loaded hain. Aap standard Web UI se in features ko switch aur use kar sakte hain.
