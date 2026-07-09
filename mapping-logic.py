//-- 1. Map initialization --//

const map = L.map('map').setView([39.5, -98.5], 4);
const streamForecasts = {};
const forecastCache = new Map();

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);


//-- 2. Clusters --//

const damCluster = L.markerClusterGroup();
const nwmCluster = L.markerClusterGroup();

map.addLayer(damCluster);
map.addLayer(nwmCluster);


//-- 3. Globals --//

let allDamFeatures = [];
let allMarkers = [];
let watershedLayer = L.layerGroup();
let selectedDam = null;
let streamMarkers = [];
let currentForecastIndex = 0;
function getDamName(props) {

    return (
        props.name ||
        props.Name ||
        props.DAM_NAME ||
        props.Dam_Name ||
        "Unnamed Dam"
    );

}

//-- 4. Styling --//

function getHazardColor(h) {
    if (h === "High") return "red";
    if (h === "Significant") return "orange";
    if (h === "Low") return "green";
    return "gray";
}

//-- 5. Filters --//

function getSelectedHazards() {
    return Array.from(
        document.querySelectorAll('.filter-box input:checked')
    ).map(cb => cb.value);
}

//-- 6. Forecast --//

function parseForecastData(data) {
    let times = [];
    let flows = [];
    // FORMAT 1
    // { times: [], flows: [] }
    if (data.times && data.flows) {
        times = data.times;
        flows = data.flows;
    }

    // FORMAT 2
    // NOAA timeSeries format

    else if (data.forecast && data.forecast.timeSeries) {
        times = data.forecast.timeSeries.map(
            d => d.validTime || d.time
        );
        flows = data.forecast.timeSeries.map(
            d => d.value || d.flow
        );
    }

    // FORMAT 3
    // Generic array

    else if (Array.isArray(data)) {
        times = data.map(
            d => d.time || d.validTime || d.datetime
        );
        flows = data.map(
            d => d.flow || d.value || d.discharge
        );
    }

    // FORMAT 4
    // Nested hydrograph object

    else if (data.hydrograph?.series) {
        times = data.hydrograph.series.map(
            d => d.time
        );
        flows = data.hydrograph.series.map(
            d => d.flow
        );
    }
    return {
        times,
        flows
    };
}

async function loadForecastForDam(feature) {
    const props = feature.properties;
    const comid =
        props.COMID ||
        props.comid ||
        props.Comid;
    if (!comid) {
        console.error(
            "Missing COMID:",
            feature
        );
        alert(
            "No COMID available for this dam."
        );
        return;
    }
    try {

        //-- Flask Forecast --//

        const response = await fetch(
            `/api/nwm_forecast/${comid}`
        );

        const ForecastData = await response.json();
        const parsedForecast = parseForecastData(ForecastData);
        const times = parsedForecast.times;
        const flows = parsedForecast.flows;

//--ANALYTICS TOGGLE--//
        const analyticsToggle =
            document.getElementById("analyticsToggle");

        if (analyticsToggle) {

           analyticsToggle.addEventListener("click", () => {

                document
                    .getElementById("analyticsSidebar")
                    .classList.toggle("open");
            });
        }

        //-- NOAA Gauge Info --//

        let gaugeData = {};

        try {
            const gaugeResponse =
                await fetch(
                    `https://api.water.noaa.gov/nwps/v1/gauges/${comid}`
                );
            if (gaugeResponse.ok) {
                gaugeData =
                    await gaugeResponse.json();
            }
        }
        catch(err) {
            console.warn(
                "Gauge lookup failed",
                err
            );
        }

        //-- Modal Elements --//

        const modal =
            document.getElementById('forecastModal');

        const statusDisplay =
            document.getElementById('statusDisplay');

        const nwmInfo =
            document.getElementById('nwmInfo');

        modal.style.display = "block";

        //-- Left Panel --//

        statusDisplay.innerHTML = `
            <h2>${getDamName(props)}</h2>

            <p><strong>COMID:</strong> ${comid}</p>

            <p><strong>Hazard:</strong>
            ${props.hazard || "N/A"}</p>
        `;

        //-- Right Panel --//

        nwmInfo.innerHTML = `
            <strong>Gauge Name:</strong>
            ${gaugeData.name || "N/A"}<br>

            <strong>Latitude:</strong>
            ${gaugeData.latitude || "N/A"}<br>

            <strong>Longitude:</strong>
            ${gaugeData.longitude || "N/A"}<br>

            <strong>Current Flow:</strong>
            ${gaugeData.flow || "N/A"} cfs<br>

            <strong>Status:</strong>
            ${gaugeData.status || "N/A"}<br>
        `;

        //-- Hydrograph --//

        const ctx =
            document.getElementById('forecastChart')
            .getContext('2d');
        if (window.forecastChart) {
            window.forecastChart.destroy();
        }
        window.forecastChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: times,
                datasets: [{
                    label: 'NWM Forecast Flow (cfs)',
                    data: flows,
                    borderWidth: 2,
                    tension: 0.25
                }]
            },

            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        ticks: {
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Flow (cfs)'
                        }
                    }
                }
            }
        });

    }
    catch(err) {
        console.error("Forecast Error:", err);
        alert("Failed to load forecast.");
    }
}

//-- 7. Render dams --//

function renderDams() {

    damCluster.clearLayers();
    allMarkers = [];
    const selected = getSelectedHazards();

    allDamFeatures.forEach(feature => {

        const hazard =
            feature.properties.hazard ||
            feature.properties.Hazard ||
            feature.properties.HAZARD;

        if (!selected.includes(hazard)) return;

        const [lon, lat] =
            feature.geometry.coordinates;

        const marker = L.circleMarker(
            [lat, lon],
            {
                radius: 6,
                fillColor: getHazardColor(hazard),
                color: "#fff",
                weight: 1,
                fillOpacity: 0.8
                marker.comid =
                parsed.comid;
            }
        );

        marker.featureData = feature;

        marker.bindTooltip(
            getDamName(feature.properties)
        );

        marker.on('click', () => {
            selectedDam = feature;
            loadForecastForDam(feature);
            openAnalyticsSidebar(feature);
        });

        damCluster.addLayer(marker);
        allMarkers.push(marker);
    });
}

//-- Sidebar Analytics --//

function openAnalyticsSidebar(feature) {

    const props = feature.properties;

    const sidebar =
        document.getElementById(
            'analyticsSidebar'
        );

    sidebar.classList.add('open');
    document.getElementById(
        'selectedDamName'
    ).textContent =
        props.name || 'Unnamed Dam';

    //-- Status Badge --//

    const hazard =
        props.hazard || 'Unknown';

    let badgeClass =
        'status-low';

    if (hazard === 'High') {
        badgeClass = 'status-high';
    }

    else if (hazard === 'Significant') {
        badgeClass = 'status-significant';
    }

    document.getElementById(
        'forecastStatusBadge'
    ).innerHTML = `
        <span class="
            status-badge
            ${badgeClass}
        ">
            ${hazard.toUpperCase()}
        </span>
    `;

    //-- Dam Info --//

    document.getElementById(
        'damInfo'
    ).innerHTML = `

        <strong>River:</strong>
        ${props.river || 'N/A'}<br>

        <strong>County:</strong>
        ${props.county || 'N/A'}<br>

        <strong>Watershed:</strong>
        ${props.watershed || 'N/A'}<br>

        <strong>COMID:</strong>
        ${props.COMID || props.comid || 'N/A'}
    `;
}

//-- 8. Load GeoPackage --//

fetch('data/dams.gpkg')

    .then(r => r.arrayBuffer())

    .then(b => geopackage.open(b))

    .then(gpkg => {

        console.log("GeoPackage loaded");

        gpkg.getFeatureTables().forEach(table => {

            const features =
                gpkg.iterateGeoJSONFeatures(table);

            for (let f of features) {

                allDamFeatures.push(f);
            }
        });

        console.log(
            "Dam count:",
            allDamFeatures.length
        );

        renderDams();

        const watersheds = new Set();

        allDamFeatures.forEach(feature => {

            const ws =
                feature.properties.watershed;

            if (ws) {
                watersheds.add(ws);
            }

        });

        const select =
            document.getElementById(
                'watershedSelect'
            );

        watersheds.forEach(ws => {

            const option =
                document.createElement('option');

            option.value = ws;
            option.textContent = ws;

            select.appendChild(option);

         });
    })

    .catch(err => {
        console.error(
            "GeoPackage Load Error:",
            err
        );
    });

//--Flow Color--//

function getFlowColor(flow)
updateStreamsAtHour(
    idx
);

function updateStreamsAtHour(
    forecastHour
) {
    streamMarkers.forEach(
        marker => {
            const forecast =
                streamForecasts[
                    marker.comid
                ];
            if (!forecast)
                return;
            const flow =
                forecast.flows[
                    forecastHour
                ];
            marker.setStyle({
                fillColor:
                    getFlowColor(
                        flow
                    ),
                radius:
                    Math.max(
                        4,
                        Math.min(
                            12,
                            Math.log10(
                                flow + 1
                            ) * 3
                        )
                    )
            });
        }
    );
}

    streamMarkers.forEach(marker => {

        const adjustedFlow =
            marker.forecastFlow *
            forecastMultiplier;

        marker.setStyle({

            fillColor:
                getFlowColor(
                    adjustedFlow
                ),

            radius:
                Math.max(
                    4,
                    Math.min(
                        12,
                        Math.log10(
                            adjustedFlow + 1
                        ) * 3
                    )
                )

        });

    });

}

//--Forecast Slider--//

forecastSlider.addEventListener("input", e => {

    const hour =
        Number(e.target.value);

    streamLayer.eachLayer(layer => {

        const forecast =
            layer.feature.properties.forecast;

        if (!forecast) return;

        const flow =
            forecast[hour].flow;

        layer.setStyle({

            color: getStreamColor(flow)

        });

    });

});

//-- 9. Load NWM --//

function parseGauge(site) {
    return {
        name:
            site.name ||
            site.gaugeName ||
            site.stationName ||
            "Unknown Gauge",
        latitude:
            site.latitude ||
            site.lat ||
            site.location?.latitude,
        longitude:
            site.longitude ||
            site.lon ||
            site.lng ||
            site.location?.longitude,
        flow:
            site.flow ||
            site.discharge ||
            site.streamflow ||
            site.value ||
            "N/A",
        status:
            site.status ||
            site.condition ||
            "Unknown"
    };
}

function loadNWM() {

    //--WHEN EACH STREAM LOADS REMOVES EXTRA API CALL--//
    async function loadForecast(streamLayer) {

    const comid = streamLayer.feature.properties.COMID;

    // Already downloaded?
    if (forecastCache.has(comid)) {

        streamLayer.feature.properties.forecast =
            forecastCache.get(comid);

        return;
    }

    const response =
        await fetch(`/api/nwm_forecast/${comid}`);

    const forecast =
        await response.json();

    forecastCache.set(comid, forecast);

//--MAKES EACH STREAM HAS feature.properties.forecast --//
    streamLayer.eachLayer(layer => {
    loadForecast(layer);
    });

        //-- NOAA may return items[] --//

        const gauges =
            data.items || data.features || data;
        if (!Array.isArray(gauges)) {
            console.error(
                "NWM response is not an array"
            );
            return;
        }

        gauges.forEach(siteRaw => {

            const site =
                siteRaw.properties || siteRaw;

            const parsed =
                parseGauge(site);

            if (!parsed.latitude || !parsed.longitude) {
                return;
            }

            const marker = L.circleMarker(
                [parsed.latitude, parsed.longitude],
                {
                    radius: 5,
                    fillColor: "blue",
                    color: "#fff",
                    fillOpacity: 0.7
                }
            );

            marker.bindTooltip(
                `<strong>${parsed.name}</strong><br>
                Flow: ${parsed.flow} cfs`,
                {
                    sticky: true
                }
            );
            nwmCluster.addLayer(marker);
            marker.forecastFlow =
                Number(parsed.flow) || 0;
            streamMarkers.push(marker);

            updateStreamColors(1);
        });
    })

    .catch(err => {

        console.error(
            "NWM Load Error:",
            err
        );
    });
}

//-- OPEN AND CLOSE SIDEBAR --//
const sidebar = document.getElementById("analyticsSidebar");

document.getElementById("analyticsToggle")
.addEventListener("click", () => {
    sidebar.classList.add("open");
});

document.getElementById("closeSidebar")
.addEventListener("click", () => {
    sidebar.classList.remove("open");
});

//-- Dam Search --//

document.getElementById(
    'searchButton'
)

.addEventListener('click', function () {

    const query =
        document.getElementById(
            'damSearch'
        )
        .value
        .toLowerCase();

    allMarkers.forEach(marker => {

        const tooltip =
            marker.getTooltip();

        if (!tooltip) return;

        const props =
            marker.featureData.properties;

        const searchText = `
        ${props.name || ''}
        ${props.river || ''}
        ${props.county || ''}
        `.toLowerCase();

        if (searchText.includes(query)) {

            map.setView(
                marker.getLatLng(),
                12
            );

            marker.openTooltip();

        const props =
            marker.featureData.properties;

        const searchText = `
        ${props.name || ''}
        ${props.river || ''}
        ${props.county || ''}
        `.toLowerCase();
        }

    });

});

loadNWM();

setInterval(loadNWM, 600000);


//-- 10. Hook filters --//

document.querySelectorAll(
    '.filter-box input'
)

.forEach(cb => {

    cb.addEventListener(
        'change',
        renderDams
    );

});

//-- Geolocation --//

document.getElementById(
    'geoLocateBtn'
)

.addEventListener('click', function () {

    navigator.geolocation.getCurrentPosition(
        function(position) {

            map.setView([
                position.coords.latitude,
                position.coords.longitude
            ], 11);

            L.circleMarker(
                [
                    position.coords.latitude,
                    position.coords.longitude
                ],
                {
                    radius: 8,
                    fillColor: 'blue',
                    color: '#fff',
                    fillOpacity: 1
                }
            )

            .addTo(map)

            .bindPopup(
                'Your Location'
            )

            .openPopup();

        }
    );

});

//-- Watershed Filter --//

document.getElementById(
    'watershedSelect'
)

.addEventListener('change', function(e) {

    const selected =
        e.target.value;

    damCluster.clearLayers();

    allMarkers.forEach(marker => {

        const feature =
            marker.featureData;

        if (!feature) return;

        const watershed =
            feature.properties.watershed;

        if (
            selected === 'all' ||
            watershed === selected
        ) {

            damCluster.addLayer(marker);
        }

    });

});

//--Flow Animation--//

    let animationTimer = null;

document.getElementById(
    'playForecast'
)

.addEventListener(
    'click',
    function() {

        const slider =
            document.getElementById(
                'forecastSlider'
            );

        if (animationTimer) {

            clearInterval(
                animationTimer
            );

            animationTimer =
                null;

            this.textContent =
                '▶ Play Forecast';

            return;
        }

        this.textContent =
            '⏸ Pause';

        animationTimer =
            setInterval(
                () => {

                    let value =
                        Number(
                            slider.value
                        );

                    value++;

                    if (
                        value >
                        Number(
                            slider.max
                        )
                    ) {

                        value = 0;

                    }

                    slider.value =
                        value;

                    slider.dispatchEvent(
                        new Event(
                            'input'
                        )
                    );

                },

                1000

            );

    }
);

//-- Layer Toggles --//

document.getElementById(
    'toggleDams'
)

.addEventListener('change', function(e) {

    if (e.target.checked) {

        map.addLayer(damCluster);

    } else {

        map.removeLayer(damCluster);
    }

});


document.getElementById(
    'toggleStreams'
)

.addEventListener('change', function(e) {

    if (e.target.checked) {

        map.addLayer(nwmCluster);

    } else {

        map.removeLayer(nwmCluster);
    }

});

//--Tab System--//
document.addEventListener('DOMContentLoaded', () => {

    const buttons =
        document.querySelectorAll('.nav-button');

    const panels =
        document.querySelectorAll('.tab-panel');

    buttons.forEach(button => {

        button.addEventListener('click', () => {

            const tab =
                button.dataset.tab;

            if (!tab) return;

            buttons.forEach(btn =>
                btn.classList.remove('active'));

            panels.forEach(panel =>
                panel.classList.remove('active'));

            button.classList.add('active');

            document
                .getElementById('tab-' + tab)
                .classList.add('active');

        });

    });

});
