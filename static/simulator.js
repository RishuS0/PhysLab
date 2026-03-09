function simulate(){

let data={

mass:mass.value,
fuel:fuel.value,
burn:burn.value,
thrust:thrust.value,
drag:drag.value,
viscosity:viscosity.value,
angle:angle.value

}

fetch("/simulate",{

method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)

})

.then(res=>res.json())
.then(data=>{

document.getElementById("plot").src=
"data:image/png;base64,"+data.plot

})

}

function uploadVideo(){

let file=document.getElementById("videoFile").files[0]

let form=new FormData()

form.append("video",file)

fetch("/process_video",{
method:"POST",
body:form
})

.then(res=>res.json())
.then(data=>{

document.getElementById("plot").src=
"data:image/png;base64,"+data.plot

})

}