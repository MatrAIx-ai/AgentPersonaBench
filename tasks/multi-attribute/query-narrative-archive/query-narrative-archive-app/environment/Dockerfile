# syntax=docker/dockerfile:1.7
#
# ArchiveWorkbench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ArchiveWorkbench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve packages", ArchiveWorkbench writes /app/output/archive_plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ArchiveWorkbench app + its autostart launcher.
COPY archiveworkbench.py /opt/archiveworkbench/archiveworkbench.py
COPY start-archiveworkbench.sh /opt/archiveworkbench/start-archiveworkbench.sh
RUN chmod +x /opt/archiveworkbench/start-archiveworkbench.sh

WORKDIR /app
