const submit = document.getElementById("sbmitBtn")


submit.addEventListener("click", async (e)=>{
    e.preventDefault()
    let eggName = document.getElementById("eggName")
    let eggHint = document.getElementById("eggHint")
    let eggMaxRedeems = document.getElementById("eggMaxRedeems")

    try {
        const res = await fetch("/api/create_egg", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                "user_id": "whatever",
                "name": eggName.value,
                "hint": eggHint.value,
                "max_redeems": eggMaxRedeems.value,
                "texture": "sometihng"
            })
        })
        const data = await res.json()
        console.log(data)
    } catch(err) {
        console.log("Failed to fetch", err)
    }
})