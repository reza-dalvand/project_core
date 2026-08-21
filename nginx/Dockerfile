FROM nginx:1.27-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# ✅ SSL cert ها از طریق volume در docker-compose mount می‌شوند
# مسیر: ./nginx/ssl/fullchain.pem و ./nginx/ssl/privkey.pem

EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]