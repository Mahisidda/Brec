# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /usr/src/app

COPY package*.json ./
RUN npm install

COPY . .

RUN echo "Docker Build Step: NEXT_PUBLIC_API_URL is set to: ${NEXT_PUBLIC_API_URL}"

# Build the Next.js production files
RUN npm run build

EXPOSE 3000

# Start in production mode
CMD ["npm", "run", "start"]
