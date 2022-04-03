# We start with the MedType server.
FROM ggvaidya/medtype-server:dev

# Reuse the `medtype` user from medtype-server.
ARG USERNAME=medtype
USER ${USERNAME}

# Create a directory for the scripts.
ARG MEDTYPE_BENCHMARKS=/opt/medtype/benchmarks
RUN mkdir ${MEDTYPE_BENCHMARKS}

# Copy this directory/repository in.
COPY --chown=${USERNAME} . ${MEDTYPE_BENCHMARKS}

# Set up a Python venv to work in.
WORKDIR ${MEDTYPE_BENCHMARKS}
RUN python3 -m venv venv
RUN . venv/bin/activate && pip3 install -r requirements.txt

# Change the workdir back to MedType so the entrypoint set by 
# ggvaidya/medtype-server continues to work.
WORKDIR /opt/medtype-as-service
