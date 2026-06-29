FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

# npm install: named volume(node_modules)이 비어있는 첫 실행 시 패키지 설치
# -H 0.0.0.0: 컨테이너 내 모든 인터페이스 바인딩 (호스트에서 localhost:3000 접근)
CMD ["sh", "-c", "npm install && npx next dev -H 0.0.0.0"]
