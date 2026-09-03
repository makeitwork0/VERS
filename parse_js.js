const fs = require('fs');
const html = fs.readFileSync('/tmp/vers_full.html', 'utf8');

// A simple regex to extract script tags (not perfect, but good enough for this)
const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let match;
let count = 0;

while ((match = scriptRegex.exec(html)) !== null) {
    const scriptContent = match[1];
    if (scriptContent.trim()) {
        count++;
        console.log(`Checking script ${count} length: ${scriptContent.length}`);
        try {
            // Using new Function to parse and compile the code without executing
            new Function(scriptContent);
            console.log(`Script ${count} parsed OK.`);
        } catch (e) {
            console.error(`Script ${count} parse ERROR:`, e.message);
        }
    }
}
