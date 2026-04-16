// 🔄 Emotion + Points update


// 🌗 DARK MODE
function toggleMode() {
    document.body.classList.toggle("dark");
}

// 🎯 AUTO POPUP HIDE
setTimeout(() => {
    document.getElementById("popup").style.display = "none";
}, 5000);
function sendEmotion() {

    fetch('/emotion')
    .then(res => res.json())
    .then(data => {

        let emotion = data.emotion;

        addMessage("You feel: " + emotion, "user");

        fetch('/get_response', {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({emotion: emotion})
        })
        .then(res => res.json())
        .then(data => {
            addMessage(data.reply, "bot");
        });

    });
}

function addMessage(text, type) {
    let box = document.getElementById("chat-box");

    let msg = document.createElement("div");
    msg.classList.add("msg", type);
    msg.innerText = text;

    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

// 🔥 UPDATE SUGGESTION + POINTS + STREAK
setInterval(async ()=>{
try{
let res = await fetch('/get_data');
let data = await res.json();

let emo = data.emotions[data.emotions.length-1] || "neutral";

// 🎯 TASK
let t = tasks[emo];
currentTask = t[Math.floor(Math.random()*t.length)];
document.getElementById("taskText").innerText = currentTask;

// 💡 SUGGESTION (FIX)
document.getElementById("suggestion").innerText =
data.suggestion || "Stay positive 💖";

// ⭐ POINTS
document.getElementById("points").innerText = data.points;

// 🔥 STREAK
document.getElementById("streak").innerText = data.streak;

}catch(e){
console.log(e);
}
},2000);

