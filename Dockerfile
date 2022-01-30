FROM python:3.9-slim-bullseye

# I can pass the environmental files in directly in the Dockerfile even if the password contains special characters; but I can also use the run command from Readme.
# ENV DB_HOST 192.168.x.x
# ENV DB_PORT 5432
# ENV DB_USER user
# ENV DB_PASS '"CP.!@X_2.Y|6D6u'
# ENV DB db

RUN apt-get update && apt install -y libpq-dev gcc cron git

COPY . /app
#RUN rm -f /app/crontab && rm -f /app/*.pbix && rm -f entrypoint.sh && rm -f /app/.env
#RUN pip install --upgrade pip --no-cache-dir && pip install -r /app/requirements.txt --no-cache-dir
RUN rm -f /app/crontab && rm -f entrypoint.sh && pip install --upgrade pip --no-cache-dir && pip install -r /app/requirements.txt --no-cache-dir

# If the crontab file is written in LF mode (VS Code has a switch for it in the toolbar) it can be written directly and used
COPY crontab /etc/cron.d/elec_crontab
RUN crontab /etc/cron.d/elec_crontab
# Otherwise an option is to echo commands into the crontab file directly:
#RUN echo "* * * * * /usr/local/bin/python3 /app/main.py >/var/log/cron.log 2>&1" > /etc/cron.d/elec_crontab
# RUN echo "* * * * * /usr/local/bin/python3 /app/script.py >/var/log/cron.log 2>&1" >> /etc/cron.d/elec_crontab && \
#     echo "* * * * * touch /var/log/random_file_cron1" >> /etc/cron.d/elec_crontab && \
#     echo "* * * * * /usr/local/bin/python3 /app/test.py" >> /etc/cron.d/elec_crontab && \
#     crontab /etc/cron.d/elec_crontab

# Copy in the entrypoint file, which will help populate the env vars for Crontab
ENTRYPOINT ["/app/entrypoint.sh"]

# Format varies depending on Linux distro
CMD ["cron", "-f", "-l", "2"]
#CMD ["crond", "-f", "-l", "2"]
#CMD ["crond", "-n"]