// ============================================================
// GLOBAL
// ============================================================

let selectedLanguage = "en-IN";
let recognition = null;

// Stores the number of AI assessments for each risk category.
// Kept in memory for the current browser session.
const chartData = {
    low: 0,
    medium: 0,
    high: 0,
    emergency: 0
};

function getElement(...ids){
    return ids
        .map((id) => document.getElementById(id))
        .find(Boolean);
}


// ============================================================
// LANGUAGE
// ============================================================

function setLanguage(language){

    selectedLanguage = language;

    const english =
        getElement("englishBtn") ||
        document.querySelector('[onclick*="setLanguage(\'en-IN\'"]');

    const tamil =
        getElement("tamilBtn") ||
        document.querySelector('[onclick*="setLanguage(\'ta-IN\'"]');

    english?.classList.remove(
        "active"
    );

    tamil?.classList.remove(
        "active"
    );

    if(language === "ta-IN"){

        tamil?.classList.add(
            "active"
        );

    }else{

        english?.classList.add(
            "active"
        );

    }
}

function escapeHtml(value = ""){
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderMedicalReport(markdown){
    const analysisText = document.getElementById("analysisText");

    if(!analysisText){
        return;
    }

    const content = String(markdown || "").replace(/\r/g, "").trim();

    if(!content){
        analysisText.innerHTML = "<p class=\"empty-state\">No analysis available yet.</p>";
        return;
    }

    const sectionOrder = [
        "Summary",
        "Possible Causes",
        "What You Can Do",
        "When To See A Doctor",
        "Emergency Warning Signs",
        "Recommended Next Step"
    ];

    const sections = {};
    let currentSection = null;

    for(const line of content.split("\n")){
        const trimmed = line.trim();

        if(!trimmed){
            continue;
        }

        const headingMatch = trimmed.match(/^###\s*(.+)$/i);

        if(headingMatch){
            currentSection = headingMatch[1].trim();
            if(!sections[currentSection]){
                sections[currentSection] = [];
            }
            continue;
        }

        if(currentSection){
            sections[currentSection].push(trimmed.replace(/^[-*]\s*/, ""));
        }
    }

    const riskMatch = content.match(/Risk Level:\s*([A-Z]+)/i);
    const specialistMatch = content.match(/Recommended Specialist:\s*(.+)/i);
    const risk = riskMatch ? riskMatch[1].toUpperCase() : "MEDIUM";
    const specialist = specialistMatch ? specialistMatch[1].trim() : "General Physician";

    let html = `
        <div class="report-header">
            <span class="report-badge ${risk.toLowerCase()}">Risk: ${escapeHtml(risk)}</span>
            <span class="report-specialist">${escapeHtml(specialist)}</span>
        </div>
    `;

    for(const title of sectionOrder){
        const body = sections[title] || [];
        if(!body.length){
            continue;
        }

        const paragraph = body
            .join(" ")
            .replace(/\s+/g, " ")
            .trim();

        html += `
            <div class="report-section">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(paragraph)}</p>
            </div>
        `;
    }

    analysisText.innerHTML = html;
}


// ============================================================
// ASK AI
// ============================================================

async function askAI(){

    const symptoms =
        document.getElementById(
            "symptoms"
        ).value.trim();

    const temperature =
        document.getElementById(
            "temperature"
        ).value.trim();

    const duration =
        document.getElementById(
            "duration"
        ).value.trim();

    const severity =
        document.getElementById(
            "severity"
        ).value;

    const mainSymptom =
        getElement(
            "mainSymptom",
            "main_symptom"
        ).value.trim();


    if(!symptoms){

        alert(
            "Please describe your symptoms first."
        );

        return;
    }


    const loading =
        document.getElementById(
            "loading"
        );

    const analysisPanel =
        document.getElementById(
            "analysis"
        );

    const riskBox =
        document.getElementById(
            "riskBox"
        );

    const specialistBox =
        document.getElementById(
            "specialistBox"
        );

    const errorBox =
        document.getElementById(
            "errorBox"
        );

    const askButton =
        getElement(
            "askButton",
            "askBtn"
        );


    if(analysisPanel){
        analysisPanel.classList.add("show");
    }

    if(riskBox){
        riskBox.style.display = "none";
    }

    if(specialistBox){
        specialistBox.style.display = "none";
    }

    if(errorBox){
        errorBox.style.display = "none";
    }


    loading.style.display =
        "flex";

    if(!askButton){
        throw new Error("Ask AI button was not found in the page.");
    }

    askButton.disabled =
        true;

    askButton.innerText =
        "⏳ Analysing...";


    try{

        const response =
            await fetch(
                "/ask-ai",
                {
                    method:"POST",

                    headers:{
                        "Content-Type":
                            "application/json",

                        "Accept":
                            "application/json"
                    },

                    body:JSON.stringify({

                        symptoms:
                            symptoms,

                        temperature:
                            temperature,

                        duration:
                            duration,

                        severity:
                            severity,

                        main_symptom:
                            mainSymptom,

                        language:
                            selectedLanguage

                    })
                }
            );


        const data =
            await response.json();


        if(
            !response.ok ||
            !data.success
        ){

            throw new Error(
                data.error ||
                "AI request failed."
            );

        }


        // ====================================================
        // RESULT
        // ====================================================

        renderMedicalReport(
            data.result || ""
        );

        if(analysisPanel){
            analysisPanel.classList.add("show");
        }


        // ====================================================
        // RISK
        // ====================================================

        const risk =
            (
                data.risk ||
                "MEDIUM"
            ).toUpperCase();


        updateRiskUI(
            risk,
            data.risk_message ||
            "This assessment is based on the symptoms you described and should be reviewed by a medical professional if symptoms worsen."
        );

        updateHealthscore(risk);


        // ====================================================
        // SPECIALIST
        // ====================================================

        const specialistElement =
            document.getElementById(
                "specialist"
            );

        if(specialistElement){
            specialistElement.innerText =
                data.specialist ||
                "General Physician";
        }

        if(specialistBox){
            specialistBox.style.display =
                "flex";
        }


        // ====================================================
        // UPDATE PIE
        // ====================================================

        updateRiskChart(
            risk
        );


        // ====================================================
        // SCROLL
        // ====================================================

        setTimeout(
            function(){

                if(analysisPanel){
                    analysisPanel.scrollIntoView({
                        behavior:"smooth",
                        block:"start"
                    });
                }

            },
            250
        );

    }

    catch(error){

        console.error(
            error
        );

        errorBox.style.display =
            "flex";

        document.getElementById(
            "errorText"
        ).innerText =
            error.message;

    }

    finally{

        loading.style.display =
            "none";

        askButton.disabled =
            false;

        askButton.innerText =
            "🤖 Ask AI";

    }

}


// ============================================================
// RISK UI
// ============================================================
function updateRiskUI(
    risk,
    message
){

    const box =
        document.getElementById(
            "riskBox"
        );

    const level =
        document.getElementById(
            "riskLevel"
        );

    if(!box || !level){
        return;
    }

    box.className = "risk-box " + risk.toLowerCase();

    if(risk === "LOW"){
        level.innerText = "LOW";
    }
    else if(risk === "HIGH"){
        level.innerText = "HIGH";
    }
    else if(risk === "EMERGENCY"){
        level.innerText = "EMERGENCY";
    }
    else{
        level.innerText = "MEDIUM";
    }

    const riskText = document.getElementById("riskText");
    if(riskText){
        riskText.innerText = message || "";
    }

    box.style.display = "block";

}


// ============================================================
// CLEAR
// ============================================================

function clearAll(){

    document.getElementById(
        "symptoms"
    ).value = "";

    document.getElementById(
        "temperature"
    ).value = "";

    document.getElementById(
        "duration"
    ).value = "";

    document.getElementById(
        "severity"
    ).value = "";

    document.getElementById(
        "main_symptom"
    ).value = "";

    const analysis = document.getElementById("analysis");
    if(analysis){
        analysis.classList.remove("show");
    }

    const analysisText = document.getElementById("analysisText");
    if(analysisText){
        analysisText.innerHTML = "";
    }

    const riskBox = document.getElementById("riskBox");
    if(riskBox){
        riskBox.style.display = "none";
    }

    const specialistBox = document.getElementById("specialistBox");
    if(specialistBox){
        specialistBox.style.display = "none";
    }

    const errorBox = document.getElementById("errorBox");
    if(errorBox){
        errorBox.style.display = "none";
    }

}


// ============================================================
// VOICE INPUT
// ============================================================

function startVoice(){

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;


    if(!SpeechRecognition){

        alert(
            "Voice recognition is not supported by this browser."
        );

        return;
    }


    recognition =
        new SpeechRecognition();


    recognition.lang =
        selectedLanguage;


    recognition.continuous =
        false;


    recognition.interimResults =
        false;


    recognition.start();


    recognition.onresult =
        function(event){

            const text =
                event.results[0][0]
                    .transcript;


            const textarea =
                document.getElementById(
                    "symptoms"
                );


            if(textarea.value){

                textarea.value +=
                    " " + text;

            }else{

                textarea.value =
                    text;

            }

        };


    recognition.onerror =
        function(event){

            console.error(
                "Voice recognition error:",
                event
            );

        };

}


// ============================================================
// VOICE CHAT
// ============================================================

function startVoiceChat(){

    startVoice();

}


// ============================================================
// STOP VOICE
// ============================================================

function stopVoice(){

    if(recognition){

        try{

            recognition.stop();

        }catch(error){

            console.log(error);

        }

        recognition = null;

    }


    if(
        window.speechSynthesis
    ){

        window.speechSynthesis.cancel();

    }

}


// ============================================================
// READ AI RESPONSE
// ============================================================

function speakAI(){

    const response =
        document.getElementById(
            "analysisText"
        ).innerText.trim();


    if(!response){

        alert(
            "Please ask AI first."
        );

        return;
    }


    if(
        !window.speechSynthesis
    ){

        alert(
            "Text-to-speech is not supported."
        );

        return;
    }


    window.speechSynthesis.cancel();


    const speech =
        new SpeechSynthesisUtterance(
            response
        );


    speech.lang =
        selectedLanguage;


    speech.rate =
        0.9;


    window.speechSynthesis.speak(
        speech
    );

}


// ============================================================
// BMI
// ============================================================

function calculateBMI(){

    const weight =
        parseFloat(
            document.getElementById(
                "weight"
            ).value
        );


    const heightCm =
        parseFloat(
            document.getElementById(
                "height"
            ).value
        );


    const result =
        document.getElementById(
            "bmiResult"
        );


    if(
        !weight ||
        !heightCm ||
        weight <= 0 ||
        heightCm <= 0
    ){

        result.innerText =
            "Enter valid height and weight.";

        return;
    }


    const height =
        heightCm / 100;


    const bmi =
        weight /
        (
            height *
            height
        );


    let category;


    if(bmi < 18.5){

        category =
            "Underweight";

    }

    else if(bmi < 25){

        category =
            "Normal range";

    }

    else if(bmi < 30){

        category =
            "Overweight";

    }

    else{

        category =
            "Obesity";

    }


    result.innerText =
        "BMI: "
        +
        bmi.toFixed(1)
        +
        " — "
        +
        category;

}


// ============================================================
// MEDICINE REMINDER
// ============================================================

async function setReminder(){

    const medicine =
        document.getElementById(
            "medicineName"
        ).value.trim();


    const time =
        document.getElementById(
            "reminderTime"
        ).value;


    const message =
        document.getElementById(
            "reminderMessage"
        );


    if(!medicine || !time){

        alert(
            "Enter medicine name and reminder time."
        );

        return;
    }


    try{

        const response =
            await fetch(
                "/medicine-reminder",
                {
                    method:"POST",

                    headers:{
                        "Content-Type":
                            "application/json"
                    },

                    body:JSON.stringify({

                        medicine_name:
                            medicine,

                        reminder_time:
                            time

                    })
                }
            );


        const data =
            await response.json();


        if(!data.success){

            throw new Error(
                data.error
            );

        }


        message.className =
            "reminder-message";


        message.innerText =
            "✓ Reminder saved for "
            +
            medicine
            +
            " at "
            +
            time;


        if(
            "Notification"
            in window
        ){

            if(
                Notification.permission ===
                "default"
            ){

                try{

                    await Notification.requestPermission();

                }catch(error){

                    console.log(error);

                }

            }

        }

    }

    catch(error){

        alert(
            "Reminder error: "
            +
            error.message
        );

    }

}


// ============================================================
// PIE CHART
// ============================================================

function getTotal(){

    return (

        chartData.low +

        chartData.medium +

        chartData.high +

        chartData.emergency

    );

}



// ============================================================
// DRAW CSS PIE CHART
// ============================================================

function drawRiskChart(){

    const pie =
        document.getElementById(
            "riskPie"
        );


    if(!pie){

        return;
    }


    const low =
        Number(chartData.low) || 0;


    const medium =
        Number(chartData.medium) || 0;


    const high =
        Number(chartData.high) || 0;


    const emergency =
        Number(chartData.emergency) || 0;


    const total =
        low +
        medium +
        high +
        emergency;


    document.getElementById(
        "chartTotal"
    ).innerText =
        total;


    document.getElementById(
        "lowCount"
    ).innerText =
        low;


    document.getElementById(
        "mediumCount"
    ).innerText =
        medium;


    document.getElementById(
        "highCount"
    ).innerText =
        high;


    document.getElementById(
        "emergencyCount"
    ).innerText =
        emergency;


    if(total === 0){

        pie.style.background =
            "#dbeafe";

        return;

    }


    const lowDeg =
        (low / total) * 360;


    const mediumDeg =
        (medium / total) * 360;


    const highDeg =
        (high / total) * 360;


    const emergencyDeg =
        (emergency / total) * 360;


    const lowEnd =
        lowDeg;


    const mediumEnd =
        lowDeg +
        mediumDeg;


    const highEnd =
        lowDeg +
        mediumDeg +
        highDeg;


    const emergencyEnd =
        lowDeg +
        mediumDeg +
        highDeg +
        emergencyDeg;


    pie.style.background =

        `conic-gradient(
            #22c55e 0deg ${lowEnd}deg,
            #f59e0b ${lowEnd}deg ${mediumEnd}deg,
            #ef4444 ${mediumEnd}deg ${highEnd}deg,
            #991b1b ${highEnd}deg ${emergencyEnd}deg
        )`;

}
function setHealthScore(score){
    const scoreValue = document.getElementById("healthScoreValue");
    const ring = document.querySelector(".score-ring");

    if(scoreValue){
        scoreValue.innerText = Math.max(0, Math.min(100, Number(score) || 88));
    }

    if(ring){
        const safeScore = Math.max(0, Math.min(100, Number(score) || 88));
        ring.style.background = `conic-gradient(#10b981 0 ${safeScore}%, #dbeafe ${safeScore}% 100%)`;
    }
}

function updateHealthscore(risk){

    let score = 88;

    if(risk==="LOW"){
        score = 92;
    }
    else if(risk==="HIGH"){
        score = 36;
    }
    else if(risk==="EMERGENCY"){
        score = 18;
    }

    setHealthScore(score);
}

// ============================================================
// UPDATE CHART AFTER AI
// ============================================================

function updateRiskChart(risk){

    if(risk === "LOW"){

        chartData.low++;

    }

    else if(risk === "MEDIUM"){

        chartData.medium++;

    }

    else if(risk === "HIGH"){

        chartData.high++;

    }

    else if(risk === "EMERGENCY"){

        chartData.emergency++;

    }


    drawRiskChart();

}


// ============================================================
// START
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function(){

        drawRiskChart();
        setHealthScore(88);

    }
);

// Backward-compatible names used by the dashboard markup.
function readAnswer(){
    speakAI();
}

function clearForm(){
    clearAll();
}
