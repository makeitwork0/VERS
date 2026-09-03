fetch('https://api.rainviewer.com/public/weather-maps.json')
    .then(r => r.json())
    .then(d => {
        const path = d.radar.past[d.radar.past.length - 1].path;
        console.log(`https://tilecache.rainviewer.com${path}/256/15/27532/14841/2/1_1.png`);
    });
