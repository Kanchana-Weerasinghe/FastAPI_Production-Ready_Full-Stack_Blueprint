{{- define "app.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "app.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "app.selector" -}}
app.kubernetes.io/name: {{ .root.Chart.Name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Image reference: digest wins over tag; tag defaults to the chart appVersion. */}}
{{- define "app.image" -}}
{{- if .image.digest -}}
{{ .image.repository }}@{{ .image.digest }}
{{- else -}}
{{ .image.repository }}:{{ .image.tag | default .root.Chart.AppVersion }}
{{- end -}}
{{- end -}}

{{- define "app.validate" -}}
{{- if or (contains "your-org" .Values.image.api.repository) (contains "your-repo" .Values.image.api.repository) (contains "your-org" .Values.image.web.repository) (contains "your-repo" .Values.image.web.repository) -}}
{{- fail "Set real image.api.repository and image.web.repository values before installing the chart." -}}
{{- end -}}
{{- if or (eq .Values.config.APP_DOMAIN "app.example.com") (eq .Values.config.APP_DOMAIN "staging.app.example.com") (eq .Values.ingress.host "app.example.com") (eq .Values.ingress.host "staging.app.example.com") -}}
{{- fail "Replace example APP_DOMAIN and ingress.host values before installing the chart." -}}
{{- end -}}
{{- if or (contains "example.com" .Values.config.CORS_ORIGINS) (contains "example.com" .Values.config.FRONTEND_URL) -}}
{{- fail "Replace example CORS_ORIGINS and FRONTEND_URL values before installing the chart." -}}
{{- end -}}
{{- if or (eq .Values.config.S3_BUCKET "your-app-uploads") (eq .Values.config.S3_BUCKET "your-app-uploads-staging") (eq .Values.config.S3_BUCKET "") -}}
{{- fail "Set config.S3_BUCKET to the environment's private uploads bucket before installing the chart." -}}
{{- end -}}
{{- if ne .Values.config.APP_DOMAIN .Values.ingress.host -}}
{{- fail "config.APP_DOMAIN and ingress.host must be the same DNS name." -}}
{{- end -}}
{{- end -}}

{{- define "app.apiEnv" -}}
envFrom:
  - configMapRef:
      name: {{ include "app.fullname" . }}
  - secretRef:
      name: {{ .Values.existingSecret }}
env:
  - name: APP_VERSION
    value: {{ .Values.image.api.tag | default .Chart.AppVersion | quote }}
{{- end -}}

{{- define "app.topologySpread" -}}
{{- if .root.Values.topologySpread }}
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        {{- include "app.selector" . | nindent 8 }}
{{- end }}
{{- end -}}
