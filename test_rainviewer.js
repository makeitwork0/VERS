fetch('https://api.rainviewer.com/public/weather-maps.json')
    .then(r => r.json())
    .then(d => {
        const past = d.radar.past;
        console.log(past[past.length - 1]);
    });
