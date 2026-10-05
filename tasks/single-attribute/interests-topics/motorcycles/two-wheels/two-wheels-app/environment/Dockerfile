# syntax=docker/dockerfile:1.7
#
# PlanMyWeekend OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlanMyWeekend native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Plan weekend", PlanMyWeekend writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlanMyWeekend app + its autostart launcher.
COPY planmyweekend.py /opt/planmyweekend/planmyweekend.py
COPY start-planmyweekend.sh /opt/planmyweekend/start-planmyweekend.sh
RUN chmod +x /opt/planmyweekend/start-planmyweekend.sh

WORKDIR /app
