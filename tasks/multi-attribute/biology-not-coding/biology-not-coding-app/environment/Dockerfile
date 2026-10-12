# syntax=docker/dockerfile:1.7
#
# SaturdaysOpenLecture OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysOpenLecture native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysOpenLecture writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysOpenLecture app + its autostart launcher.
COPY saturdaysopenlecture.py /opt/saturdaysopenlecture/saturdaysopenlecture.py
COPY start-saturdaysopenlecture.sh /opt/saturdaysopenlecture/start-saturdaysopenlecture.sh
RUN chmod +x /opt/saturdaysopenlecture/start-saturdaysopenlecture.sh

WORKDIR /app
