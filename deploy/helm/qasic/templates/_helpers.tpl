{{/*
Expand the name of the chart.
*/}}
{{- define "qasic.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "qasic.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "qasic.redis.host" -}}
{{- if .Values.redis.enabled -}}
{{- include "qasic.fullname" . }}-redis:{{ .Values.redis.port }}
{{- else -}}
{{- .Values.redis.externalHost | default "redis:6379" }}
{{- end -}}
{{- end -}}

{{- define "qasic.postgres.url" -}}
{{- if .Values.postgres.enabled -}}
postgresql://{{ .Values.postgres.user }}:{{ .Values.postgres.password | default "qasic" }}@{{ include "qasic.fullname" . }}-postgres:{{ .Values.postgres.port }}/{{ .Values.postgres.db }}
{{- else -}}
{{- .Values.postgres.externalUrl | default "postgresql://qasic:qasic@postgres:5432/qasic" }}
{{- end -}}
{{- end -}}

{{- define "qasic.celery.broker" -}}
redis://{{ include "qasic.redis.host" . }}
{{- end -}}
