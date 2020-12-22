
function drawGraph(data, color_val, y_min_id, y_max_id, x_min_id, x_max_id) {
    // Clear the chart box.
    document.getElementById('chart-box').innerHTML = '';    
    // set the dimensions and margins of the graph
    var margin = {top: 30, left: 30, bottom: 30, right: 30},
        width = 1640 - margin.left - margin.right, /* window width about 1920px; left width 180~280px; */
        height = 720 - margin.top - margin.bottom; /* window height about 820px; */
    // append the svg object to the body of the page
    var svg = d3.select("#chart-box")
        .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
        .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    // dirawing parms
    const y_min  = d3.min(data.y);
    const y_max  = d3.max(data.y);
    const x_min  = d3.min(data.x);
    const x_max  = d3.max(data.x);
    var y_fr = y_min;
    var y_to = y_max;
    var x_fr = x_min;
    var x_to = x_max;
    if (y_max > y_min_id.value && y_min_id.value > y_min) { y_fr = y_min_id.value; };
    if (x_max > x_min_id.value && x_min_id.value > x_min) { x_fr = x_min_id.value; };
    if (y_max > y_max_id.value && y_max_id.value > y_min) { y_to = y_max_id.value; };
    if (x_max > x_max_id.value && x_max_id.value > x_min) { x_to = x_max_id.value; };
    if (x_fr < 0.01) { x_fr = 0.0 } // adjust binnary error 
    // Add X axis
    var x = d3.scaleLinear()
        .domain([ x_fr, x_to ])
        .range([ 0, width ]);
    svg.append("g")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x));
    // Add Y axis
    var y = d3.scaleLinear()
        .domain([ y_fr, y_to ])
        .range([ height, 0 ]);
    svg.append("g")
        .call(d3.axisLeft(y));
    // setting scale parms
    y_min_id.value = y_min;
    y_max_id.value = y_max;
    x_min_id.value = x_min;
    x_max_id.value = x_max;
    //
    var points = [];
    data.x.forEach((value, i) => {
        points.push({x: value, y: data.y[i]});
    });
    // Add the line
    svg.append("path")
        .datum(points)
        .attr("fill", "none")
        .attr("stroke", color_val)
        .attr("stroke-width", 1.0)
        .attr("d", d3.line()
            .x(function(d) { return x(d.x) })
            .y(function(d) { return y(d.y) })
        );
}

function clearScale() {
    if ( ! document.getElementById("scale_manu").checked ) {
        document.getElementById("y_min").value = '';
        document.getElementById("y_max").value = '';
        document.getElementById("x_min").value = '';
        document.getElementById("x_max").value = '';
    }
}    

function setAutoScale() {
    document.getElementById("scale_auto").checked  = true
    document.getElementById("scale_manu").disabled  = true   
    document.getElementById("y_min").value = '';
    document.getElementById("y_max").value = '';
    document.getElementById("x_min").value = '';
    document.getElementById("x_max").value = '';
}    