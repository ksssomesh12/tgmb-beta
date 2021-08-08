FROM ubuntu:latest as base
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y aria2 curl ffmpeg jq libc++-dev locales nano pv python3 python3-pip python3-lxml tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8

FROM ubuntu:latest as api
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y git gperf make cmake clang-10 libc++-dev libc++abi-dev libssl-dev zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /root
RUN git clone --recursive https://github.com/tdlib/telegram-bot-api.git && cd telegram-bot-api && \
    git checkout 81f2983 && mkdir build && cd build && \
    CXXFLAGS="-stdlib=libc++" CC=/usr/bin/clang-10 CXX=/usr/bin/clang++-10 \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. && \
    cmake --build . --target install -- -j $(nproc) && cd .. && \
    ls -l bin/telegram-bot-api*

FROM ghcr.io/ksssomesh12/tgmb-beta:base as app-base
FROM ghcr.io/ksssomesh12/tgmb-beta:api as app-api

FROM scratch as app
COPY --from=app-base / /
COPY --from=app-api /root/telegram-bot-api/bin/telegram-bot-api /usr/bin/telegram-bot-api
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8' TZ='Asia/Kolkata'
WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "-m", "tgmb"]
