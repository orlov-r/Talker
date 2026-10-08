FROM debian:bookworm-slim AS builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential git ca-certificates scons pkg-config \
 && rm -rf /var/lib/apt/lists/*

ARG RHVOICE_REF=master
WORKDIR /src
RUN git clone https://github.com/RHVoice/RHVoice.git . \
 && git checkout "$RHVOICE_REF" \
 && git submodule update --init --recursive \
      external/libs/boost \
      data/languages/Georgian \
      data/voices/natia

RUN scons -j2 languages=georgian audio_libs=none prefix=/usr/local \
 && scons install languages=georgian audio_libs=none \
      prefix=/usr/local DESTDIR=/stage \
 && find /stage/usr/local/lib -type f -name '*.so*' \
      -exec strip --strip-unneeded {} + \
 && strip --strip-unneeded /stage/usr/local/bin/RHVoice-test \
 && mkdir -p /stage/usr/local/share/doc/rhvoice-source \
 && git rev-parse HEAD \
      > /stage/usr/local/share/doc/rhvoice-source/commit.txt \
 && cp LICENSE.md /stage/usr/local/share/doc/rhvoice-source/

FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 libstdc++6 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /stage/usr/local/bin/RHVoice-test /usr/local/bin/
COPY --from=builder /stage/usr/local/lib/ /usr/local/lib/
COPY --from=builder /stage/usr/local/share/ /usr/local/share/
COPY --from=builder /stage/usr/local/etc/ /usr/local/etc/
RUN ldconfig

# Fail the build if Natia cannot produce a valid, nonempty WAV.
RUN printf 'გამარჯობა! როგორ ხარ?\n' \
      | RHVoice-test -p Natia -o /tmp/check.wav \
 && python3 -c "import wave; w=wave.open('/tmp/check.wav'); assert w.getnframes()>0; print(w.getparams())" \
 && rm /tmp/check.wav

WORKDIR /app
COPY server.py /app/server.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
EXPOSE 8080
CMD ["python3", "/app/server.py"]
