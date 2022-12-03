FROM ubuntu:jammy as api
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y git gperf make cmake clang-14 libc++-dev libc++abi-dev libssl-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /root
COPY api api
RUN cd api && rm -rf .git && mkdir build && cd build && \
    CXXFLAGS="-stdlib=libc++" CC=/usr/bin/clang-14 CXX=/usr/bin/clang++-14 \
    cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. && \
    cmake --build . --target install -- -j $(nproc) && cd .. && \
    ls -lh bin/telegram-bot-api*

FROM ubuntu:jammy as sdk
ENV DEBIAN_FRONTEND='noninteractive'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y autoconf automake gcc g++ git libtool make python3 python3-dev python3-distutils python3-pip && \
    apt-get install -y libc-ares-dev libcrypto++-dev libcurl4-openssl-dev libfreeimage-dev libsodium-dev && \
    apt-get install -y libsqlite3-dev libssl-dev swig zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /root
COPY sdk sdk
COPY ac-m4-py.patch .
RUN cd sdk && rm -rf .git && mv ../ac-m4-py.patch ./ && git apply ac-m4-py.patch && ./clean.sh && ./autogen.sh && \
    ./configure --disable-examples --disable-silent-rules --enable-python --with-sodium && \
    make -j $(nproc) && cd bindings/python/ && python3 setup.py bdist_wheel && \
    ls -lh dist/megasdk*

FROM ubuntu:jammy as app
COPY --from=api /root/api/bin/telegram-bot-api /usr/bin/telegram-bot-api
COPY --from=sdk /root/sdk /root/sdk
ENV DEBIAN_FRONTEND='noninteractive'
ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8' TZ='Asia/Kolkata'
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y aria2 curl ffmpeg jq locales nano pv python3 python3-pip python3-lxml tzdata && \
    apt-get install -y libc++-dev libmagic-dev libcrypto++-dev libfreeimage-dev software-properties-common && \
    add-apt-repository ppa:qbittorrent-team/qbittorrent-stable && \
    apt-get install -y qbittorrent-nox && \
    apt-get purge -y software-properties-common && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
RUN locale-gen en_US.UTF-8
RUN pip3 install --no-cache-dir /root/sdk/bindings/python/dist/megasdk-*.whl
WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY Pipfile .
COPY grt.py .
RUN python3 grt.py && pip3 install --no-cache-dir -r requirements.txt
COPY tgmb tgmb
CMD ["python3", "-m", "tgmb"]
