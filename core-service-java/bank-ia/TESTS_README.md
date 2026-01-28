# 🧪 Guía de Tests

## 📋 Estructura de Tests

```
src/test/java/com/bank/bank_ia/
├── validators/
│   └── RefinanceValidatorTest.java          # Tests unitarios del validador
├── services/impl/
│   ├── LoanBuilderTest.java                 # Tests unitarios del builder
│   └── RefinanceOperationServiceImplTest.java # Tests unitarios del servicio (con mocks)
└── controllers/
    └── ClaimControllerIntegrationTest.java   # Tests de integración (con TestContainers)
```

## 🎯 Cobertura de Tests

### ✅ Tests Unitarios

1. **RefinanceValidatorTest**
   - ✅ Validación de solicitud válida
   - ✅ Validación de lista vacía
   - ✅ Validación de lista null
   - ✅ Validación de préstamos no encontrados
   - ✅ Validación de propiedad de préstamos
   - ✅ Validación de monto insuficiente
   - ✅ Validación de monto exacto

2. **LoanBuilderTest**
   - ✅ Construcción correcta de préstamo
   - ✅ Cálculo correcto de cuota
   - ✅ Generación de números únicos
   - ✅ Uso de prefijo configurado

3. **RefinanceOperationServiceImplTest**
   - ✅ Ejecución exitosa de refinanciación
   - ✅ Eliminación de ofertas
   - ✅ Cierre de préstamos antiguos
   - ✅ Manejo de errores de validación
   - ✅ Cálculo correcto de cash out

### ✅ Tests de Integración

1. **ClaimControllerIntegrationTest**
   - ✅ Refinanciación exitosa (end-to-end)
   - ✅ Validación de monto insuficiente
   - ✅ Validación de lista vacía
   - ✅ Verificación de cambios en BD

## 🚀 Ejecutar Tests

### Todos los tests
```bash
mvn test
```

### Solo tests unitarios
```bash
mvn test -Dtest=*Test
```

### Solo tests de integración
```bash
mvn test -Dtest=*IntegrationTest
```

### Test específico
```bash
mvn test -Dtest=RefinanceValidatorTest
```

## 📊 Cobertura de Código

Para generar reporte de cobertura con JaCoCo:

```bash
mvn clean test jacoco:report
```

El reporte se generará en: `target/site/jacoco/index.html`

## 🛠️ Tecnologías Usadas

- **JUnit 5**: Framework de testing
- **Mockito**: Mocking para tests unitarios
- **AssertJ**: Assertions fluidas
- **TestContainers**: Contenedores Docker para tests de integración
- **MockMvc**: Testing de controllers Spring

## 📝 Buenas Prácticas Aplicadas

1. **Nombres descriptivos**: `@DisplayName` para claridad
2. **Arrange-Act-Assert**: Estructura clara en cada test
3. **Aislamiento**: Cada test es independiente
4. **Mocks apropiados**: Solo mockear dependencias externas
5. **Tests de integración**: Con BD real (TestContainers)

## 🔍 Ejemplos

### Test Unitario (con Mocks)
```java
@ExtendWith(MockitoExtension.class)
class ServiceTest {
    @Mock
    private Repository repository;
    
    @InjectMocks
    private Service service;
    
    @Test
    void shouldDoSomething() {
        // Arrange
        when(repository.findById(any())).thenReturn(optional);
        
        // Act
        Result result = service.doSomething();
        
        // Assert
        assertThat(result).isNotNull();
    }
}
```

### Test de Integración (con TestContainers)
```java
@SpringBootTest
@Testcontainers
class ControllerIntegrationTest {
    @Container
    static PostgreSQLContainer<?> postgres = 
        new PostgreSQLContainer<>("postgres:15-alpine");
    
    @Test
    void shouldExecuteEndpoint() {
        // Test con BD real
    }
}
```

## ⚠️ Notas Importantes

1. **TestContainers requiere Docker**: Asegúrate de tener Docker corriendo
2. **Tests de integración son más lentos**: Se ejecutan con BD real
3. **Limpieza automática**: `@BeforeEach` limpia datos antes de cada test
4. **Aislamiento**: Cada test usa su propia instancia de BD

## 📈 Próximos Pasos

- [ ] Agregar tests para `AccountService`
- [ ] Agregar tests para `LoanService`
- [ ] Agregar tests para `RefinanceResetService`
- [ ] Aumentar cobertura a >80%
- [ ] Agregar tests de performance
