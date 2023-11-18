    // Set the date we're counting down to
var countDownDate = new Date
countDownDate.setMinutes(countDownDate.getMinutes() + 3);

// Update the count down every 1 second
var x = setInterval(function () {

    // Get today's date and time
    var now = new Date().getTime();

    // Find the distance between now and the count down date
    var distance = countDownDate - now;

    // Time calculations for days, hours, minutes and seconds
    var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    var seconds = Math.floor((distance % (1000 * 60)) / 1000);

    // Output the result in an element with id="demo"
    document.getElementById("resend-code").innerHTML = `<p>${seconds} : ${minutes}  to resend code</p>`

    // If the count down is over, write some text
    if (distance < 0) {
        clearInterval(x);
        document.getElementById("resend-code").innerHTML = resendForm
    }
}, 1000);

