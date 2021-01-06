//
// js for Sensor Data Minitoring & Analysis System(WSN application)
//

var tid = null;
var col = 'black';
var row_val;
var dat_val;
var row_col = new Array();
var i;

function monBegin(is_mobile) {
    // control UI before function run
    disableAllMenus(is_mobile);           
    document.getElementById("btn_start").disabled = true;
    monStart(0, is_mobile);
}

function monStart(value, is_mobile) {
    const interval = document.getElementById('tm_interval').value;
    axios.post('/post_monStart', {
        value: value,
    }).then(response => {
        const data = response.data;
        //console.log(data);
        dispData(data);
        if (data.timer == 'on' & value < 10) {
            i = value + 1
            tid = setTimeout(monStart, Number(interval)*1000, i, is_mobile);
            document.getElementById("btn_stop" ).disabled = false;
        } else {
            //enableAllMenus(is_mobile);
            monStop(is_mobile)
        }  
    }).catch(function (error) {
        alert('Error occurred on submit: ' + error);
    });
}

function monStop(is_mobile) {
    // control UI before function run
    disableAllMenus(is_mobile);           
    document.getElementById("btn_start").disabled = false;
    document.getElementById("btn_stop" ).disabled = true;
    const value = document.getElementById('tm_interval').value;
    clearTimeout ( tid );
    axios.post('/post_monStop', {
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

function dispData(data) {        
    for ( i = 1; i  < 12; i++ ) { 
        row_val = parseFloat( document.getElementById("row_" + i).innerHTML );
        dat_val = parseFloat( data.row[i] );
        if (row_val > dat_val) { col = 'blue'; } else { 
            if (row_val < dat_val) { col = 'red'; } else { col = 'black'; } 
        }
        row_col[i] = col;
    }

    document.getElementById("row_0").innerHTML = data.row[0]; // time
    for ( i = 1; i  < 12; i++ ) { 
        if ( data.row[i] != '*' ) {   
            document.getElementById("row_" + i).innerHTML = data.row[i]; //.fontcolor(row_col[i]);
        }    
        document.getElementById("row_" + i).style.color = row_col[i];
    }
    for ( i = 0; i  < 2; i++ ) { 
        document.getElementById("status_" + i).innerHTML = data.status[i];
    }    

    if (data.status[0] == 'UNKNOWN') {
        col = "gray";
    } else {
        if (data.status[0] == 'VIBRATION') { col = 'blue'; } else { col = 'black'; }
    }    
    document.getElementById("status_0").style.color = col;
    if (data.status[1] == 'UNKNOWN') {
        col = "gray";
    } else {
        if (data.status[1] == 'ABNORMAL') { col = 'red'; } else { col = 'black'; }
    }    
    document.getElementById("status_1").style.color = col;
}
