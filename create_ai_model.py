from tensorflow.keras import layers, models

# Simple segmentation CNN (lightweight demo model)
def build_model():
    inputs = layers.Input((256, 256, 3))

    x = layers.Conv2D(16, 3, activation='relu', padding='same')(inputs)
    x = layers.MaxPooling2D()(x)

    x = layers.Conv2D(32, 3, activation='relu', padding='same')(x)
    x = layers.UpSampling2D()(x)

    outputs = layers.Conv2D(1, 1, activation='sigmoid')(x)

    model = models.Model(inputs, outputs)
    model.compile(optimizer='adam', loss='binary_crossentropy')
    return model

model = build_model()
model.save("sand_ai_model.h5")

print("AI model created successfully")
