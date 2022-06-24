FROM ubuntu:focal as base
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y aria2 curl ffmpeg jq libc++-dev locales nano pv python3 python3-pip python3-lxml tzdata && \
    rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8

FROM ubuntu:focal as api
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y git gperf make cmake clang-10 libc++-dev libc++abi-dev libssl-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /root
RUN git clone --recursive https://github.com/tdlib/telegram-bot-api.git && cd telegram-bot-api && \
    git checkout 24ee05d && git submodule update && mkdir build && cd build && \
    CXXFLAGS="-stdlib=libc++" CC=/usr/bin/clang-10 CXX=/usr/bin/clang++-10 \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. && \
    cmake --build . --target install -- -j $(nproc) && cd .. && \
    ls -lh bin/telegram-bot-api*

FROM ubuntu:focal as mega
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y autoconf automake gcc g++ git libtool make python3 python3-dev python3-distutils python3-pip && \
    apt-get install -y libc-ares-dev libcrypto++-dev libcurl4-openssl-dev libfreeimage-dev libsodium-dev && \
    apt-get install -y libsqlite3-dev libssl-dev swig zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /root
RUN git clone https://github.com/meganz/sdk.git mega-sdk/ && cd mega-sdk/ && \
    git checkout v3.12.2 && \
    ./autogen.sh && ./configure --disable-silent-rules --enable-python --with-sodium --disable-examples && \
    make -j $(nproc) && cd bindings/python/ && python3 setup.py bdist_wheel && \
    ls -lh dist/megasdk*

FROM ghcr.io/ksssomesh12/tgmb-beta:base as app-base
FROM ghcr.io/ksssomesh12/tgmb-beta:api as app-api
FROM ghcr.io/ksssomesh12/tgmb-beta:mega as app-mega

FROM scratch as app
COPY --from=app-base / /
COPY --from=app-api /root/telegram-bot-api/bin/telegram-bot-api /usr/bin/telegram-bot-api
COPY --from=app-mega /root/mega-sdk /root/mega-sdk
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8' TZ='Asia/Kolkata'
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y libcrypto++-dev libfreeimage-dev && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:qbittorrent-team/qbittorrent-stable && \
    apt-get install -y qbittorrent-nox && \
    apt-get purge -y software-properties-common && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir /root/mega-sdk/bindings/python/dist/megasdk-*.whl
WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "-m", "tgmb"]
