# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /usr/src/app

# Declare the build argument
ARG NEXT_PUBLIC_API_URL

COPY package*.json ./
RUN npm install

COPY . .

# Set as environment variable for the build process
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN echo "Docker Build Step: NEXT_PUBLIC_API_URL is set to: ${NEXT_PUBLIC_API_URL}"

# Build the Next.js production files
RUN npm run build

EXPOSE 3000

# Start in production mode
CMD ["npm", "run", "start"]
