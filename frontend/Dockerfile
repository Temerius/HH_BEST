FROM node:20-alpine

WORKDIR /app

# Копирование package файлов
COPY package*.json ./

# Установка зависимостей
RUN npm install

# Копирование кода
COPY . .

# Проброс порта
EXPOSE 3000

# Запуск dev сервера
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

