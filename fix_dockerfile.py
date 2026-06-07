dockerfile = open('Dockerfile', 'r', encoding='utf-8').read()

node_stage = '''# Stage 0: Frontend Builder
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

'''

copy_dist = 'COPY --from=frontend-builder /app/frontend/dist ./frontend/dist\n'

# Add node stage at the top
new = node_stage + dockerfile

# Add dist copy before ENV line
new = new.replace('ENV PRISMA_PYTHON_BINARY_CACHE_DIR', copy_dist + 'ENV PRISMA_PYTHON_BINARY_CACHE_DIR')

open('Dockerfile', 'w', encoding='utf-8').write(new)
print('SUCCESS')