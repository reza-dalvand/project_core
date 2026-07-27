FROM nginx:1.27-alpine

# حذف کانفیگ پیش‌فرض
RUN rm /etc/nginx/conf.d/default.conf

# کپی کانفیگ
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]