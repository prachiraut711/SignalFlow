FROM node:22-alpine

WORKDIR /app

# Install dependencies first for layer caching
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run development server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
