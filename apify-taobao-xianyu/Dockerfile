FROM apify/actor-node-puppeteer:20

COPY package.json ./

RUN npm --quiet set progress=false \
 && npm install --only=production --no-audit --no-fund \
 && npm install --production=false --no-audit --no-fund

COPY . ./

RUN npm run build --if-present

ENV NODE_ENV=production

CMD ["node", "src/main.js"]
