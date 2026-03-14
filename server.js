const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const TEMPLATES_DIR = path.join(__dirname, 'templates');

// Ensure templates directory exists
if (!fs.existsSync(TEMPLATES_DIR)) {
    fs.mkdirSync(TEMPLATES_DIR);
}

// Ensure default template exists
const defaultTemplatePath = path.join(TEMPLATES_DIR, 'MG Road, Bangalore.json');
if (!fs.existsSync(defaultTemplatePath)) {
    const defaultTemplate = {
        shape: '5x4',
        gridData: {
            '0-0':{size:'s',blockId:'s-1'},'0-1':{size:'s',blockId:'s-1'},
            '0-2':{size:'s',blockId:'s-2'},'0-3':{size:'s',blockId:'s-2'},
            '1-0':{size:'m',blockId:'m-1'},'1-1':{size:'m',blockId:'m-1'},'2-0':{size:'m',blockId:'m-1'},'2-1':{size:'m',blockId:'m-1'},
            '1-2':{size:'m',blockId:'m-2'},'1-3':{size:'m',blockId:'m-2'},'2-2':{size:'m',blockId:'m-2'},'2-3':{size:'m',blockId:'m-2'},
            '3-0':{size:'l',blockId:'l-1'},'3-1':{size:'l',blockId:'l-1'},'3-2':{size:'l',blockId:'l-1'},'4-0':{size:'l',blockId:'l-1'},'4-1':{size:'l',blockId:'l-1'},'4-2':{size:'l',blockId:'l-1'},
            '3-3':{size:'xl',blockId:'xl-1'},'4-3':{size:'xl',blockId:'xl-1'}
        }
    };
    fs.writeFileSync(defaultTemplatePath, JSON.stringify(defaultTemplate, null, 2));
}

const defaultTemplatePath2 = path.join(TEMPLATES_DIR, 'Airport Terminal 1.json');
if (!fs.existsSync(defaultTemplatePath2)) {
    const defaultTemplate2 = {
        shape: '6x6',
        gridData: {
            '0-0':{size:'s',blockId:'s-1'},'0-1':{size:'s',blockId:'s-1'},'0-2':{size:'s',blockId:'s-2'},'0-3':{size:'s',blockId:'s-2'},'0-4':{size:'s',blockId:'s-3'},'0-5':{size:'s',blockId:'s-3'},
            '1-0':{size:'m',blockId:'m-1'},'1-1':{size:'m',blockId:'m-1'},'2-0':{size:'m',blockId:'m-1'},'2-1':{size:'m',blockId:'m-1'},
            '1-2':{size:'m',blockId:'m-2'},'1-3':{size:'m',blockId:'m-2'},'2-2':{size:'m',blockId:'m-2'},'2-3':{size:'m',blockId:'m-2'},
            '1-4':{size:'m',blockId:'m-3'},'1-5':{size:'m',blockId:'m-3'},'2-4':{size:'m',blockId:'m-3'},'2-5':{size:'m',blockId:'m-3'},
            '3-0':{size:'l',blockId:'l-1'},'3-1':{size:'l',blockId:'l-1'},'3-2':{size:'l',blockId:'l-1'},'4-0':{size:'l',blockId:'l-1'},'4-1':{size:'l',blockId:'l-1'},'4-2':{size:'l',blockId:'l-1'},
            '3-3':{size:'l',blockId:'l-2'},'3-4':{size:'l',blockId:'l-2'},'3-5':{size:'l',blockId:'l-2'},'4-3':{size:'l',blockId:'l-2'},'4-4':{size:'l',blockId:'l-2'},'4-5':{size:'l',blockId:'l-2'},
            '5-0':{size:'xl',blockId:'xl-1'},'5-1':{size:'xl',blockId:'xl-1'},'5-2':{size:'xl',blockId:'xl-1'},'5-3':{size:'xl',blockId:'xl-1'},
            '5-4':{size:'xl',blockId:'xl-2'},'5-5':{size:'xl',blockId:'xl-2'},
        }
    };
    fs.writeFileSync(defaultTemplatePath2, JSON.stringify(defaultTemplate2, null, 2));
}

const server = http.createServer((req, res) => {
    // CORS headers just in case
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        return res.end();
    }

    if (req.method === 'GET' && (req.url === '/' || req.url === '/index.html')) {
        let filePath = path.join(__dirname, 'index.html');
        fs.readFile(filePath, (err, content) => {
            if (err) {
                res.writeHead(500);
                res.end(`Error loading index.html: ${err.code}`);
            } else {
                res.writeHead(200, { 'Content-Type': 'text/html' });
                res.end(content, 'utf-8');
            }
        });
        return;
    }

    if (req.url.startsWith('/api/templates')) {
        if (req.method === 'GET') {
            fs.readdir(TEMPLATES_DIR, (err, files) => {
                if (err) {
                    res.writeHead(500);
                    return res.end(JSON.stringify({ error: 'Failed to read templates directory' }));
                }
                const templates = {};
                for (let file of files) {
                    if (file.endsWith('.json')) {
                        const name = file.slice(0, -5);
                        try {
                            const data = JSON.parse(fs.readFileSync(path.join(TEMPLATES_DIR, file), 'utf8'));
                            templates[name] = data;
                        } catch (e) {
                            console.error(`Failed to parse ${file}`);
                        }
                    }
                }
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(templates));
            });
            return;
        }

        if (req.method === 'POST') {
            let body = '';
            req.on('data', chunk => body += chunk.toString());
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const name = data.name;
                    const templateData = data.template;
                    
                    if (!name || !templateData) {
                        res.writeHead(400);
                        return res.end(JSON.stringify({ error: 'Missing name or template data' }));
                    }

                    // simple sanitization
                    const safeName = name.replace(/[^a-z0-9 ,.\-_]/gi, '');
                    const filePath = path.join(TEMPLATES_DIR, `${safeName}.json`);
                    
                    fs.writeFileSync(filePath, JSON.stringify(templateData, null, 2));
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ success: true, name: safeName }));
                } catch (e) {
                    res.writeHead(500);
                    res.end(JSON.stringify({ error: 'Failed to save template' }));
                }
            });
            return;
        }

        if (req.method === 'DELETE') {
            const urlPath = decodeURIComponent(req.url);
            const name = urlPath.split('/').pop();
            const safeName = name.replace(/[^a-z0-9 ,.\-_]/gi, '');
            const filePath = path.join(TEMPLATES_DIR, `${safeName}.json`);

            if (fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true }));
            } else {
                res.writeHead(404);
                res.end(JSON.stringify({ error: 'Template not found' }));
            }
            return;
        }
    }

    res.writeHead(404);
    res.end('Not found');
});

server.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}/`);
    console.log(`Templates are saved in: ${TEMPLATES_DIR}`);
});
