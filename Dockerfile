FROM ubuntu:latest as app-base
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y aria2 curl jq libc++-dev locales nano pv python3 python3-pip python3-lxml tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8' TZ='Asia/Kolkata'

FROM ubuntu:latest as app-compile
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y git gperf make cmake clang-10 libc++-dev libc++abi-dev libssl-dev zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /root
RUN git clone --recursive https://github.com/tdlib/telegram-bot-api.git && \
    cd telegram-bot-api && git checkout 81f2983 && mkdir build && cd build && \
    CXXFLAGS="-stdlib=libc++" CC=/usr/bin/clang-10 CXX=/usr/bin/clang++-10 \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=/usr .. && \
    cmake --build . --target install -- -j $(nproc) && \
    cd ../.. && rm -rf telegram-bot-api && \
    ls -l /usr/bin/telegram-bot-api*

FROM ghcr.io/ksssomesh12/tgmb-beta:app-base as base
FROM ghcr.io/ksssomesh12/tgmb-beta:app-compile as compile

FROM scratch as app-final
COPY --from=base / /
COPY --from=compile /usr/bin/telegram-bot-api /usr/bin
WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "-m", "tgmb"]
