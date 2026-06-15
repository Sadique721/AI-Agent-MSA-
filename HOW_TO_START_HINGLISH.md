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
Android app ke code ko compile aur build karne ke liye `android_app` directory me jake Gradle build command run karein:
```bash
cd "d:\My Self Details\Programs\AI\msa_agent\android_app"
.\gradlew.bat assembleDebug
```
> 💡 **Note**: Jab build successful ho jaye, to aapka latest APK `android_app\app\build\outputs\apk\debug\app-debug.apk` par bankar ready ho jayega.

---

### Step 5: Emulator Par APK Install Aur Start Karein
Naye compiled APK ko emulator me install karne ke liye main directory se ye command run karein:
```bash
cd "d:\My Self Details\Programs\AI\msa_agent"
& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r "d:\My Self Details\Programs\AI\msa_agent\android_app\app\build\outputs\apk\debug\app-debug.apk"
```
Install hone ke baad, app ko emulator me directly start karne ke liye:
```bash
& "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msa.agent/.MainActivity
```
App open hone par status check karein:
- Top right corner me green color me **Agent Online** status aana chahiye (iska matlab emulator host loopback IP `10.0.2.2:5000` ke through Python server se connected hai).

---

### Step 6: Unit Tests Ko Run Karein (Verification Ke Liye)
Agar aapko saare backend logic, coding generator, validator, aur review system ke unit tests check karne hain, to project ke main path se pytest command run karein:
```bash
python -m pytest
```
> 🧪 **Result**: Saare **419 test cases** 100% pass hone chahiye bina kisi error ke.

---

## 📱 Developer/Coding Agent Activities Ko Kaise Launch Karein
Agar aapko coding activities ko direct open karna hai bina main chat app ke, to aap niche likhe adb commands ka use kar sakte hain:

1. **Code Reviewer Activity** (Code grading aur comments ke liye):
   ```bash
   & "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msa.agent/.CodeReviewActivity
   ```
2. **StackTrace Analyzer Activity** (Crash traces trace karne ke liye):
   ```bash
   & "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msa.agent/.StackTraceActivity
   ```
3. **Project Generator Activity** (Scaffolding generate karne ke liye):
   ```bash
   & "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msa.agent/.ProjectGeneratorActivity
   ```
4. **History Log Activity** (Past compile activity check karne ke liye):
   ```bash
   & "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.msa.agent/.CodingHistoryActivity
   ```
