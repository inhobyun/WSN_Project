//
// js for Sensor Data Minitoring & Analysis System(WSN application)
//

function disableAllMenus(is_mobile) {
    document.getElementById("btn_ihome").disabled = true;
    document.getElementById("btn_monit").disabled = true;
    document.getElementById("btn_mon_A").disabled = true;
    document.getElementById("btn_about").disabled = true;
    if (is_mobile!='Y') {
        document.getElementById("btn_confi").disabled = true;
        document.getElementById("btn_acqui").disabled = true;
        document.getElementById("btn_gtime").disabled = true;
        document.getElementById("btn_gfreq").disabled = true;        
    }
}
    
function enableAllMenus(is_mobile) {
    document.getElementById("btn_ihome").disabled = false;
    document.getElementById("btn_monit").disabled = false;
    document.getElementById("btn_mon_A").disabled = false;
    document.getElementById("btn_about").disabled = false;
    if (is_mobile != 'Y') {
        document.getElementById("btn_confi").disabled = false;
        document.getElementById("btn_acqui").disabled = false;
        document.getElementById("btn_gtime").disabled = false;
        document.getElementById("btn_gfreq").disabled = false;        
    }
}
