# Add project specific ProGuard rules here.

# Gson はリフレクションで DTO をシリアライズ/デシリアライズするため、
# リリースビルド（minifyEnabled=true）でフィールドが消失しないよう keep する。
-keep class com.filmy.app.data.api.dto.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
