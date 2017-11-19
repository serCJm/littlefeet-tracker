window.onload = function() {

    // get modal
    var modal = document.getElementById("formActivity");

    // get button to open modal
    var btn = document.getElementById("addActivity");

    // get span element that closes the form
    var close = document.getElementsByClassName("close")[0];

    // when the user clicks on the button, open the form 
    btn.onclick = function() {
        modal.style.display = "block";
    }

    // when user clicks, close the form
    close.onclick = function() {
        modal.style.display = "none";
    }

    // when clicks outside modal, close it
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    /* ARC CHART FOR HISTORY PAGE USING D3 */
    
}