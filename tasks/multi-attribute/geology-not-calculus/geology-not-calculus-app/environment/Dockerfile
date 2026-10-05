# syntax=docker/dockerfile:1.7
#
# SaturdaysPublicLecture OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysPublicLecture native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysPublicLecture writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysPublicLecture app + its autostart launcher.
COPY saturdayspubliclecture.py /opt/saturdayspubliclecture/saturdayspubliclecture.py
COPY start-saturdayspubliclecture.sh /opt/saturdayspubliclecture/start-saturdayspubliclecture.sh
RUN chmod +x /opt/saturdayspubliclecture/start-saturdayspubliclecture.sh

WORKDIR /app
