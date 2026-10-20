{{- define "svc.name" -}}
{{- required "serviceName is required" .Values.serviceName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "svc.labels" -}}
app.kubernetes.io/name: {{ include "svc.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | default .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: domain-services
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "svc.selector" -}}
app.kubernetes.io/name: {{ include "svc.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Image reference: digest wins over tag; tag defaults to the chart appVersion. */}}
{{- define "svc.image" -}}
{{- $repo := required "image.repository is required" .Values.image.repository -}}
{{- if .Values.image.digest -}}
{{ $repo }}@{{ .Values.image.digest }}
{{- else -}}
{{ $repo }}:{{ .Values.image.tag | default .Chart.AppVersion }}
{{- end -}}
{{- end -}}

{{- define "svc.validate" -}}
{{- if or (contains "your-org" .Values.image.repository) (contains "your-repo" .Values.image.repository) -}}
{{- fail "Set a real image.repository before installing the chart." -}}
{{- end -}}
{{- if not .Values.config.DB_SCHEMA -}}
{{- fail "config.DB_SCHEMA is required: every domain service owns its own schema." -}}
{{- end -}}
{{- if not .Values.existingSecret -}}
{{- fail "existingSecret is required (DB credentials and JWT_SECRET_KEY)." -}}
{{- end -}}
{{- if or (not .Values.config.PROBLEM_TYPE_BASE_URI) (contains "example.com" .Values.config.PROBLEM_TYPE_BASE_URI) -}}
{{- fail "Set config.PROBLEM_TYPE_BASE_URI to your error documentation URL." -}}
{{- end -}}
{{- end -}}
