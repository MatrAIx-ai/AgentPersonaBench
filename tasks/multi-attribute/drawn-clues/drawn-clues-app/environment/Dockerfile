# syntax=docker/dockerfile:1.7
#
# LoanShelf OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LoanShelf native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Borrow loans", LoanShelf writes /app/output/loans.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LoanShelf app + its autostart launcher.
COPY loanshelf.py /opt/loanshelf/loanshelf.py
COPY start-loanshelf.sh /opt/loanshelf/start-loanshelf.sh
RUN chmod +x /opt/loanshelf/start-loanshelf.sh

WORKDIR /app
