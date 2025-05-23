# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /usr/src/app

COPY package*.json ./
RUN npm install

COPY . .

# Build the Next.js production files
RUN npm run build

EXPOSE 3000

# Start in production mode
CMD ["npm", "run", "start"]
