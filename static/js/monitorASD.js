//
// js for Sensor Data Minitoring & Analysis System(WSN application)
//

var tid = null;
var col = 'black';
var row_val;
var dat_val;
var row_col = new Array();
var i;

function monASDbegin(is_mobile) {
    // control UI before function run
    disableAllMenus(is_mobile);           
    document.getElementById("btn_startASD").disabled = true;
    monASDstart(0, is_mobile);
}

function monASDstart(value, is_mobile) {
    const interval = document.getElementById('tm_interval').value;
    axios.post('/post_monASDstart', {
        value: value,
    }).then(response => {
        const data = response.data;
        //console.log(data);
        dispData(data);
        if (data.timer == 'on' & value < 10) {
            i = value + 1
            tid = setTimeout(monASDstart, Number(interval)*1000, i, is_mobile);
            document.getElementById("btn_stopASD" ).disabled = false;
        } else {
            //enableAllMenus(is_mobile);
            monASDstop(is_mobile)
        }  
    }).catch(function (error) {
        alert('Error occurred on submit: ' + error);
    });
}

function monASDstop(is_mobile) {
    // control UI before function run
    disableAllMenus(is_mobile);           
    document.getElementById("btn_startASD").disabled = false;
    document.getElementById("btn_stopASD" ).disabled = true;
    const value = document.getElementById('tm_interval').value;
    clearTimeout ( tid );
    axios.post('/post_monASDstop', {
        //value: Number(value),
    }).then(response => {
        const data = response.data;
        //console.log(data);
        dispData(data);
    }).catch(function (error) {
        alert('Error occurred on submit: ' + error);
    });
    // control UI after function run
    enableAllMenus(is_mobile);           
}

function dispASDdata(data) {        
    alert('ASD monitoring has not been implemented yet !');
}
