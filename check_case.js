const fs = require('fs');
const path = require('path');
const srcDir = path.resolve('frontend/src');

function walk(dir) {
    let results = [];
    fs.readdirSync(dir).forEach(f => {
        let p = path.join(dir, f);
        if (fs.statSync(p).isDirectory()) {
            results = results.concat(walk(p));
        } else {
            if (p.endsWith('.js') || p.endsWith('.jsx')) results.push(p);
        }
    });
    return results;
}

const files = walk(srcDir);
files.forEach(file => {
    const content = fs.readFileSync(file, 'utf-8');
    const regex = /import\s+.*?\s+from\s+['"](.*?)['"]/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
        const imp = match[1];
        if (imp.startsWith('.')) {
            let targetDir = path.resolve(path.dirname(file), path.dirname(imp));
            let targetName = path.basename(imp);
            
            if (fs.existsSync(targetDir)) {
                let actualFiles = fs.readdirSync(targetDir);
                let foundExact = false;
                for (let af of actualFiles) {
                    if (af === targetName || af === targetName + '.js' || af === targetName + '.jsx') {
                        foundExact = true;
                        break;
                    }
                }
                if (!foundExact) {
                    let foundIgnoreCase = false;
                    for (let af of actualFiles) {
                        if (af.toLowerCase() === targetName.toLowerCase() || af.toLowerCase() === targetName.toLowerCase() + '.js' || af.toLowerCase() === targetName.toLowerCase() + '.jsx') {
                            foundIgnoreCase = af;
                            break;
                        }
                    }
                    if (foundIgnoreCase) {
                        console.log('CASE MISMATCH: ' + file + ' -> ' + targetName + ' (actual: ' + foundIgnoreCase + ')');
                    }
                }
            }
        }
    }
});
console.log('DONE');
